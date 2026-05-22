from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render

from apps.ledger.services import (
    budget_status,
    current_balance,
    goal_status,
    household_members,
    month_start,
)
from apps.reports.services import (
    PERIOD_CHOICES,
    income_vs_expense,
    net_worth_over_time,
    resolve_period,
    source_breakdown,
    spending_by_category,
    top_transactions,
)
from apps.transactions.models import Category, Source, Transaction


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
    from apps.ledger.services import user_household

    members = household_members(request.user)
    other_members = [m for m in members if m.id != request.user.id]

    period_key = request.GET.get("period") or "last_30"
    period = resolve_period(
        period_key, _parse_date(request.GET.get("start")), _parse_date(request.GET.get("end"))
    )
    person = request.GET.get("person") or "me"
    category_id = request.GET.get("category") or None
    source_id = request.GET.get("source") or None
    source_ids = [source_id] if source_id else None

    scoped_users = _scoped_users(request.user, members, person)
    owner_ids = [u.id for u in scoped_users]

    # Headline balance + net-worth trend
    balance = sum((current_balance(u) for u in scoped_users), Decimal("0"))
    breakdown = (
        [{"user": u, "balance": current_balance(u)} for u in scoped_users]
        if len(scoped_users) > 1
        else []
    )

    # This-period income/expense totals
    period_qs = Transaction.objects.filter(
        owner_id__in=owner_ids, occurred_on__gte=period.start, occurred_on__lte=period.end
    )
    if source_ids:
        period_qs = period_qs.filter(source_id__in=source_ids)
    sums = period_qs.aggregate(
        income=Sum("amount", filter=Q(kind="income")),
        expense=Sum("amount", filter=Q(kind="expense")),
    )
    income_total = sums["income"] or 0
    expense_total = sums["expense"] or 0

    today = date.today()
    latest = list(
        Transaction.objects.filter(owner_id__in=owner_ids, occurred_on__lte=today)
        .select_related("source", "category", "owner", "owner__profile", "recurring_rule")
        .order_by("-occurred_on", "-created_at")[:6]
    )

    # Budgets + goals are personal to the signed-in user
    budgets = budget_status(request.user, month_start(today))
    goals = [goal_status(g) for g in request.user.goals.filter(archived_at__isnull=True)]

    donut = (
        {"has_data": False, "options": {}}
        if category_id
        else spending_by_category(period, owner_ids=owner_ids, source_ids=source_ids)
    )

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
        "source_id": source_id,
        "available_categories": Category.objects.for_user(request.user).active().order_by("kind", "name"),
        "available_sources": Source.objects.for_household(user_household(request.user)).active().order_by("name"),
        "balance": balance,
        "breakdown": breakdown,
        "income_total": income_total,
        "expense_total": expense_total,
        "net_total": income_total - expense_total,
        "latest": latest,
        "budgets": budgets,
        "goals": goals,
        "net_worth": net_worth_over_time(period, user_ids=owner_ids),
        "income_vs_expense": income_vs_expense(
            period, owner_ids=owner_ids, source_ids=source_ids, category_id=category_id
        ),
        "spending_by_category": donut,
        "source_breakdown": source_breakdown(period, owner_ids=owner_ids),
        "top_transactions": top_transactions(
            period, owner_ids=owner_ids, source_ids=source_ids, category_id=category_id
        ),
    }
    template = "dashboard/_panels.html" if request.headers.get("HX-Request") else "dashboard.html"
    return render(request, template, ctx)


def health(request):
    return JsonResponse({"status": "ok"})
