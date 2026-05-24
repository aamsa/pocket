from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.transactions.models import Category

from .services import (
    PERIOD_CHOICES,
    income_vs_expense,
    period_totals,
    resolve_period,
    scope_owner_ids,
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
    period_key = request.GET.get("period") or "last_30"
    custom_start = _parse_date(request.GET.get("start"))
    custom_end = _parse_date(request.GET.get("end"))
    period = resolve_period(period_key, custom_start, custom_end)

    person = request.GET.get("person") or "me"
    category_id = request.GET.get("category") or None

    owner_ids = scope_owner_ids(request.user, person)

    available_categories = (
        Category.objects.for_user(request.user).active().order_by("kind", "name")
    )
    selected_category = None
    if category_id:
        selected_category = next(
            (c for c in available_categories if str(c.id) == category_id), None
        )

    totals = period_totals(period, owner_ids=owner_ids, category_id=category_id)

    ctx = {
        "period_key": period_key,
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "custom_start": custom_start.isoformat() if custom_start else "",
        "custom_end": custom_end.isoformat() if custom_end else "",
        "person": person,
        "category_id": category_id,
        "selected_category": selected_category,
        "available_categories": available_categories,
        "income_total": totals["income"],
        "expense_total": totals["expense"],
        "net_total": totals["net"],
        "income_vs_expense": income_vs_expense(
            period, owner_ids=owner_ids, category_id=category_id
        ),
        "spending_by_category": spending_by_category(
            period, owner_ids=owner_ids, category_id=category_id
        ),
        "top_transactions": top_transactions(
            period, owner_ids=owner_ids, category_id=category_id
        ),
    }
    template = "reports/_panels.html" if request.headers.get("HX-Request") else "reports/index.html"
    return render(request, template, ctx)
