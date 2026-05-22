from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.transactions.models import Category, Source

from .services import (
    PERIOD_CHOICES,
    income_vs_expense,
    net_worth_over_time,
    resolve_period,
    scope_owner_ids,
    source_breakdown,
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
    from apps.ledger.services import household_user_ids, user_household

    period_key = request.GET.get("period") or "last_30"
    custom_start = _parse_date(request.GET.get("start"))
    custom_end = _parse_date(request.GET.get("end"))
    period = resolve_period(period_key, custom_start, custom_end)

    person = request.GET.get("person") or "me"
    category_id = request.GET.get("category") or None
    source_id = request.GET.get("source") or None

    owner_ids = scope_owner_ids(request.user, person)
    nw_user_ids = household_user_ids(request.user) if person == "household" else [request.user.id]

    available_categories = (
        Category.objects.for_user(request.user).active().order_by("kind", "name")
    )
    available_sources = (
        Source.objects.for_household(user_household(request.user)).active().order_by("name")
    )
    source_ids = [source_id] if source_id else None

    donut = (
        {"has_data": False, "options": {}}
        if category_id
        else spending_by_category(period, owner_ids=owner_ids, source_ids=source_ids)
    )

    ctx = {
        "period_key": period_key,
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "custom_start": custom_start.isoformat() if custom_start else "",
        "custom_end": custom_end.isoformat() if custom_end else "",
        "person": person,
        "category_id": category_id,
        "source_id": source_id,
        "available_categories": available_categories,
        "available_sources": available_sources,
        "income_vs_expense": income_vs_expense(
            period, owner_ids=owner_ids, source_ids=source_ids, category_id=category_id
        ),
        "spending_by_category": donut,
        "source_breakdown": source_breakdown(period, owner_ids=owner_ids),
        "net_worth": net_worth_over_time(period, user_ids=nw_user_ids),
        "top_transactions": top_transactions(
            period, owner_ids=owner_ids, source_ids=source_ids, category_id=category_id
        ),
    }
    template = "reports/_panels.html" if request.headers.get("HX-Request") else "reports/index.html"
    return render(request, template, ctx)
