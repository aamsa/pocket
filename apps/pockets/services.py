"""Pocket-related queries that span apps. Keep view-layer code thin."""

from decimal import Decimal

from .models import Pocket


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


def balance_for(pocket, *, include_descendants=False, as_of=None):
    """Computed balance for a pocket. Returns Decimal('0') until Phase 4
    lands the Transaction/Transfer models."""
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
