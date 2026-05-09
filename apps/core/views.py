from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render

from apps.pockets.models import (
    SHARE_STATUS_PENDING,
    Pocket,
    PocketShare,
)
from apps.pockets.permissions import visible_pocket_ids
from apps.pockets.services import balance_for
from apps.transactions.models import Transaction


def _month_range(today=None):
    today = today or date.today()
    start = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    return start, next_month


@login_required
def dashboard(request):
    visible_ids = visible_pocket_ids(request.user)

    visible_pockets = list(
        Pocket.objects.filter(pk__in=visible_ids)
        .select_related("owner", "owner__profile")
        .order_by("-is_main", "owner_id", "name")
    )

    total_balance = sum(
        (balance_for(p, include_descendants=False) for p in visible_pockets),
        Decimal("0"),
    )

    month_start, next_month = _month_range()
    txn_qs = Transaction.objects.filter(
        pocket_id__in=visible_ids,
        occurred_on__gte=month_start,
        occurred_on__lt=next_month,
    )
    sums = txn_qs.values("kind").annotate(total=Sum("amount"))
    by_kind = {row["kind"]: row["total"] for row in sums}
    income_total = by_kind.get("income", 0) or 0
    expense_total = by_kind.get("expense", 0) or 0

    latest = list(
        Transaction.objects.filter(pocket_id__in=visible_ids)
        .select_related("pocket", "category")
        .order_by("-occurred_on", "-created_at")[:6]
    )

    pending_invites = (
        PocketShare.objects.filter(
            shared_with=request.user, status=SHARE_STATUS_PENDING
        )
        .select_related("pocket", "invited_by", "invited_by__profile")
    )

    own_pockets = [p for p in visible_pockets if p.owner_id == request.user.id]
    shared_count = len(visible_pockets) - len(own_pockets)

    return render(
        request,
        "dashboard.html",
        {
            "total_balance": total_balance,
            "income_total": income_total,
            "expense_total": expense_total,
            "month_label": month_start.strftime("%B %Y"),
            "latest": latest,
            "pending_invites": pending_invites,
            "own_count": len(own_pockets),
            "shared_count": shared_count,
        },
    )


def health(request):
    return JsonResponse({"status": "ok"})
