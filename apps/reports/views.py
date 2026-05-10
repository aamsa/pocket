from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.pockets.models import Pocket
from apps.pockets.permissions import visible_pocket_ids

from .services import (
    PERIOD_CHOICES,
    income_vs_expense,
    pocket_balances_over_time,
    resolve_period,
    scope_pocket_ids,
    spending_by_category,
    top_transactions,
)


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@login_required
def index(request):
    period_key = request.GET.get("period") or "month"
    custom_start = _parse_date(request.GET.get("start"))
    custom_end = _parse_date(request.GET.get("end"))
    period = resolve_period(period_key, custom_start, custom_end)

    pocket_id = request.GET.get("pocket") or None
    include_children = request.GET.get("include_children") == "on"

    pocket_ids = scope_pocket_ids(request.user, pocket_id, include_children)

    visible_pockets = (
        Pocket.objects.filter(pk__in=visible_pocket_ids(request.user))
        .select_related("owner", "owner__profile")
        .order_by("name")
    )

    if pocket_id:
        chosen = next((p for p in visible_pockets if str(p.id) == pocket_id), None)
        if chosen is not None:
            balance_series_name = (
                f"{chosen.name} (downstream)" if include_children else chosen.name
            )
        else:
            balance_series_name = "Overall"
    else:
        balance_series_name = "Overall"

    ctx = {
        "period_key": period_key,
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "custom_start": custom_start.isoformat() if custom_start else "",
        "custom_end": custom_end.isoformat() if custom_end else "",
        "pocket_id": pocket_id,
        "include_children": include_children,
        "visible_pockets": visible_pockets,
        "income_vs_expense": income_vs_expense(request.user, period, pocket_ids),
        "spending_by_category": spending_by_category(request.user, period, pocket_ids),
        "pocket_balances": pocket_balances_over_time(
            request.user, period, pocket_ids, series_name=balance_series_name
        ),
        "balance_series_name": balance_series_name,
        "top_transactions": top_transactions(request.user, period, pocket_ids),
    }
    template = "reports/_panels.html" if request.headers.get("HX-Request") else "reports/index.html"
    return render(request, template, ctx)
