"""Pocket-related queries that span apps. Keep view-layer code thin."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from .models import (
    POCKET_KIND_CREDIT,
    SHARE_STATUS_ACCEPTED,
    Pocket,
    PocketShare,
)


def user_pocket_tree(user):
    """Return a list of (pocket, depth) tuples in display order: pre-order DFS,
    Main first, then children sorted alphabetically. Archived pockets excluded.
    """
    pockets = list(Pocket.objects.owned_by(user).active())
    by_parent = {}
    for p in pockets:
        by_parent.setdefault(p.parent_id, []).append(p)
    for siblings in by_parent.values():
        siblings.sort(key=lambda p: (not p.is_main, p.name.lower()))

    rows = []

    def walk(parent_id, depth):
        for child in by_parent.get(parent_id, []):
            rows.append((child, depth))
            walk(child.id, depth + 1)

    walk(None, 0)
    return rows


def shared_pocket_groups(user):
    """Return a list of {'owner', 'rows': [(pocket, depth)], 'permission'} dicts
    for pockets shared with `user`. Each shared root pocket forms its own
    sub-tree, with children also displayed if they exist."""
    shares = (
        PocketShare.objects.filter(shared_with=user, status=SHARE_STATUS_ACCEPTED)
        .select_related("pocket", "pocket__owner", "pocket__owner__profile")
    )
    if not shares:
        return []

    # Walk descendants per share via in-memory tree walk over owner's pockets.
    groups_by_owner = {}
    for share in shares:
        root = share.pocket
        if root.archived_at is not None:
            continue
        owner = root.owner
        siblings = list(Pocket.objects.owned_by(owner).active())
        by_parent = {}
        for p in siblings:
            by_parent.setdefault(p.parent_id, []).append(p)

        rows = []

        def walk(node, depth):
            rows.append((node, depth, share.permission))
            for child in sorted(
                by_parent.get(node.id, []), key=lambda p: p.name.lower()
            ):
                walk(child, depth + 1)

        walk(root, 0)
        groups_by_owner.setdefault(owner.id, {"owner": owner, "rows": []})["rows"].extend(rows)

    return list(groups_by_owner.values())


def balance_for(pocket, *, include_descendants=False, as_of=None):
    """Computed balance for a pocket. Optional `as_of` caps the date window."""
    try:
        from apps.transactions.models import Transaction, Transfer  # noqa: F401
    except ImportError:
        return Decimal("0")

    pocket_ids = (
        pocket.descendant_ids_with_self() if include_descendants else [pocket.id]
    )

    txn_qs = Transaction.objects.filter(pocket_id__in=pocket_ids)
    transfer_in_qs = Transfer.objects.filter(to_pocket_id__in=pocket_ids)
    transfer_out_qs = Transfer.objects.filter(from_pocket_id__in=pocket_ids)

    # When include_descendants is True, transfers wholly within the subtree
    # net out and shouldn't be counted against the subtree balance.
    if include_descendants:
        transfer_in_qs = transfer_in_qs.exclude(from_pocket_id__in=pocket_ids)
        transfer_out_qs = transfer_out_qs.exclude(to_pocket_id__in=pocket_ids)

    if as_of is not None:
        txn_qs = txn_qs.filter(occurred_on__lte=as_of)
        transfer_in_qs = transfer_in_qs.filter(occurred_on__lte=as_of)
        transfer_out_qs = transfer_out_qs.filter(occurred_on__lte=as_of)

    income = txn_qs.filter(kind="income").aggregate(s=models_sum("amount"))["s"] or 0
    expense = txn_qs.filter(kind="expense").aggregate(s=models_sum("amount"))["s"] or 0
    transfer_in = transfer_in_qs.aggregate(s=models_sum("amount"))["s"] or 0
    transfer_out = transfer_out_qs.aggregate(s=models_sum("amount"))["s"] or 0

    return Decimal(income) - Decimal(expense) + Decimal(transfer_in) - Decimal(transfer_out)


def models_sum(field):
    from django.db.models import Sum

    return Sum(field)


# ---------------------------------------------------------------------------
# Credit-card cycle helpers
# ---------------------------------------------------------------------------


@dataclass
class CardCycle:
    outstanding: Decimal       # total currently owed (≥ 0)
    cycle_spend: Decimal       # expenses in the current (open) cycle
    pending_bill: Decimal      # closed-statement amount still due
    cycle_start: date          # day after the previous statement close
    due_on: date               # next due date
    days_until_due: int


def _clamp_day_to_month(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _shift_month(d: date, delta: int) -> tuple[int, int]:
    total = d.month - 1 + delta
    return d.year + total // 12, total % 12 + 1


def previous_statement_close(card: Pocket, today: date) -> date:
    """Most recent date `<= today` where day == card.statement_day.

    Statement_day is constrained to 1..28 in the model so month-day clamping
    isn't strictly necessary, but the helper handles it defensively.
    """
    if today.day >= card.statement_day:
        return _clamp_day_to_month(today.year, today.month, card.statement_day)
    year, month = _shift_month(today, -1)
    return _clamp_day_to_month(year, month, card.statement_day)


def next_due_date(card: Pocket, today: date) -> date:
    """Next date strictly after `today` where day == card.due_day."""
    if today.day < card.due_day:
        candidate = _clamp_day_to_month(today.year, today.month, card.due_day)
        if candidate > today:
            return candidate
    year, month = _shift_month(today, 1)
    return _clamp_day_to_month(year, month, card.due_day)


def card_cycle(card: Pocket, today: date | None = None) -> CardCycle:
    """Compute the active cycle snapshot for a credit-card pocket."""
    from apps.transactions.models import Transaction

    if card.kind != POCKET_KIND_CREDIT:
        raise ValueError("card_cycle requires a credit-kind pocket")

    today = today or date.today()
    last_close = previous_statement_close(card, today)
    cycle_start = last_close + timedelta(days=1)

    cycle_spend = (
        Transaction.objects.filter(
            pocket=card, kind="expense", occurred_on__gte=cycle_start, occurred_on__lte=today
        )
        .aggregate(s=models_sum("amount"))["s"]
        or 0
    )
    cycle_spend = Decimal(cycle_spend)

    outstanding_signed = -balance_for(card)
    outstanding = max(Decimal("0"), outstanding_signed)

    # Whatever was accrued before the current cycle started, minus payments —
    # i.e. the closed statement that the user must pay next.
    pending_bill = max(Decimal("0"), outstanding - cycle_spend)

    due_on = next_due_date(card, today)
    days_until_due = (due_on - today).days

    return CardCycle(
        outstanding=outstanding,
        cycle_spend=cycle_spend,
        pending_bill=pending_bill,
        cycle_start=cycle_start,
        due_on=due_on,
        days_until_due=days_until_due,
    )
