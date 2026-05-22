from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import BudgetForm, GoalContributeForm, GoalForm, RecurringRuleForm
from .models import Budget, Goal, RecurringRule
from .services import _shift_month, budget_status, goal_status, month_start


def _parse_month(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value).replace(day=1)
    except ValueError:
        return None


# --- Budgets ----------------------------------------------------------------


@login_required
def budgets_index(request):
    month = _parse_month(request.GET.get("month")) or month_start(date.today())
    rows = budget_status(request.user, month)
    py, pm = _shift_month(month, -1)
    ny, nm = _shift_month(month, 1)
    ctx = {
        "month": month,
        "rows": rows,
        "total_limit": sum((r["limit"] for r in rows), Decimal("0")),
        "total_spent": sum((r["spent"] for r in rows), Decimal("0")),
        "prev_month": date(py, pm, 1),
        "next_month": date(ny, nm, 1),
    }
    return render(request, "ledger/budgets/index.html", ctx)


@login_required
@require_http_methods(["GET", "POST"])
def budget_new(request):
    month = _parse_month(request.GET.get("month")) or month_start(date.today())
    if request.method == "POST":
        month = _parse_month(request.POST.get("month")) or month
        form = BudgetForm(request.POST, user=request.user, month=month)
        if form.is_valid():
            form.save()
            messages.success(request, "Budget saved.")
            return redirect(reverse("ledger:budgets") + f"?month={month.isoformat()}")
        return render(request, "ledger/budgets/form.html", {"form": form, "mode": "new", "month": month})
    form = BudgetForm(user=request.user, month=month)
    return render(request, "ledger/budgets/form.html", {"form": form, "mode": "new", "month": month})


@login_required
@require_http_methods(["GET", "POST"])
def budget_edit(request, budget_id):
    budget = get_object_or_404(Budget, pk=budget_id, user=request.user)
    if request.method == "POST":
        form = BudgetForm(request.POST, instance=budget, user=request.user, month=budget.month)
        if form.is_valid():
            form.save()
            messages.success(request, "Budget updated.")
            return redirect("ledger:budgets")
    else:
        form = BudgetForm(instance=budget, user=request.user, month=budget.month)
    return render(request, "ledger/budgets/form.html", {"form": form, "mode": "edit", "budget": budget, "month": budget.month})


@login_required
@require_http_methods(["POST"])
def budget_delete(request, budget_id):
    budget = get_object_or_404(Budget, pk=budget_id, user=request.user)
    budget.delete()
    messages.success(request, "Budget removed.")
    return redirect("ledger:budgets")


# --- Goals ------------------------------------------------------------------


@login_required
def goals_index(request):
    goals = [
        goal_status(g) for g in Goal.objects.filter(user=request.user, archived_at__isnull=True)
    ]
    return render(request, "ledger/goals/index.html", {"goals": goals})


@login_required
@require_http_methods(["GET", "POST"])
def goal_new(request):
    if request.method == "POST":
        form = GoalForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Goal created.")
            return redirect("ledger:goals")
    else:
        form = GoalForm(user=request.user)
    return render(request, "ledger/goals/form.html", {"form": form, "mode": "new"})


@login_required
@require_http_methods(["GET", "POST"])
def goal_edit(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id, user=request.user)
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Goal updated.")
            return redirect("ledger:goals")
    else:
        form = GoalForm(instance=goal, user=request.user)
    return render(request, "ledger/goals/form.html", {"form": form, "mode": "edit", "goal": goal})


@login_required
@require_http_methods(["POST"])
def goal_contribute(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id, user=request.user)
    form = GoalContributeForm(request.POST)
    if form.is_valid():
        goal.current_amount = max(Decimal("0"), Decimal(goal.current_amount) + form.cleaned_data["amount"])
        goal.save(update_fields=["current_amount", "updated_at"])
        messages.success(request, "Goal updated.")
    else:
        messages.error(request, "Enter a valid amount.")
    return redirect("ledger:goals")


@login_required
@require_http_methods(["POST"])
def goal_delete(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id, user=request.user)
    goal.archived_at = timezone.now()
    goal.save(update_fields=["archived_at", "updated_at"])
    messages.success(request, "Goal archived.")
    return redirect("ledger:goals")


# --- Recurring --------------------------------------------------------------


@login_required
def recurring_index(request):
    rules = RecurringRule.objects.filter(owner=request.user).select_related("category", "source")
    return render(
        request,
        "ledger/recurring/index.html",
        {
            "active_rules": [r for r in rules if r.active],
            "paused_rules": [r for r in rules if not r.active],
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def recurring_new(request):
    if request.method == "POST":
        form = RecurringRuleForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Recurring entry created.")
            return redirect("ledger:recurring")
    else:
        form = RecurringRuleForm(user=request.user)
    return render(request, "ledger/recurring/form.html", {"form": form, "mode": "new"})


@login_required
@require_http_methods(["GET", "POST"])
def recurring_edit(request, rule_id):
    rule = get_object_or_404(RecurringRule, pk=rule_id, owner=request.user)
    if request.method == "POST":
        form = RecurringRuleForm(request.POST, instance=rule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Recurring entry updated.")
            return redirect("ledger:recurring")
    else:
        form = RecurringRuleForm(instance=rule, user=request.user)
    return render(request, "ledger/recurring/form.html", {"form": form, "mode": "edit", "rule": rule})


@login_required
@require_http_methods(["POST"])
def recurring_toggle(request, rule_id):
    rule = get_object_or_404(RecurringRule, pk=rule_id, owner=request.user)
    rule.active = not rule.active
    rule.save(update_fields=["active", "updated_at"])
    messages.success(request, "Recurring entry " + ("resumed." if rule.active else "paused."))
    return redirect("ledger:recurring")


@login_required
@require_http_methods(["POST"])
def recurring_delete(request, rule_id):
    rule = get_object_or_404(RecurringRule, pk=rule_id, owner=request.user)
    rule.delete()
    messages.success(request, "Recurring entry deleted.")
    return redirect("ledger:recurring")
