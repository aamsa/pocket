"""Pocket-related queries that span apps. Keep view-layer code thin."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from .models import (
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
    """Computed balance for a pocket as of a point in time.

    `as_of` defaults to today, so future-dated Transactions materialised by a
    RecurringRule do NOT inflate the realised balance. Callers that need a
    forward-looking projected balance should pass `as_of=date.max` or a
    specific future date.
    """
    try:
        from apps.transactions.models import Transaction, Transfer  # noqa: F401
    except ImportError:
        return Decimal("0")

    if as_of is None:
        as_of = date.today()

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
