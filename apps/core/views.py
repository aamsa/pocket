from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.ledger.services import (
    budget_status,
    goal_status,
    household_members,
    month_start,
)
from apps.reports.services import (
    PERIOD_CHOICES,
    income_vs_expense,
    period_totals,
    resolve_period,
    spending_by_category,
    top_transactions,
)
from apps.transactions.models import Category, Transaction


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _scoped_users(request_user, members, person):
    if person == "household":
        return members
    if person and person != "me":
        chosen = [m for m in members if str(m.id) == person]
        if chosen:
            return chosen
    return [request_user]


@login_required
def dashboard(request):
    members = household_members(request.user)
    other_members = [m for m in members if m.id != request.user.id]

    period_key = request.GET.get("period") or "last_30"
    period = resolve_period(
        period_key, _parse_date(request.GET.get("start")), _parse_date(request.GET.get("end"))
    )
    person = request.GET.get("person") or "me"
    category_id = request.GET.get("category") or None

    scoped_users = _scoped_users(request.user, members, person)
    owner_ids = [u.id for u in scoped_users]

    available_categories = (
        Category.objects.for_user(request.user).active().order_by("kind", "name")
    )
    selected_category = None
    if category_id:
        selected_category = next(
            (c for c in available_categories if str(c.id) == category_id), None
        )

    # Period income/expense/net — honours the active category filter.
    totals = period_totals(period, owner_ids=owner_ids, category_id=category_id)

    today = date.today()
    latest = list(
        Transaction.objects.filter(owner_id__in=owner_ids, occurred_on__lte=today)
        .select_related("category", "owner", "owner__profile", "recurring_rule")
        .order_by("-occurred_on", "-created_at")[:6]
    )

    # Budgets + goals are personal to the signed-in user
    budgets = budget_status(request.user, month_start(today))
    goals = [goal_status(g) for g in request.user.goals.filter(archived_at__isnull=True)]

    ctx = {
        "period_key": period_key,
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "custom_start": request.GET.get("start", ""),
        "custom_end": request.GET.get("end", ""),
        "person": person,
        "members": members,
        "other_members": other_members,
        "category_id": category_id,
        "selected_category": selected_category,
        "available_categories": available_categories,
        "income_total": totals["income"],
        "expense_total": totals["expense"],
        "net_total": totals["net"],
        "latest": latest,
        "budgets": budgets,
        "goals": goals,
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
    template = "dashboard/_panels.html" if request.headers.get("HX-Request") else "dashboard.html"
    return render(request, template, ctx)


def health(request):
    return JsonResponse({"status": "ok"})
