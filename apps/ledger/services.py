"""Money-domain business logic. Keep view-layer code thin.

Covers: household scoping, recurring-rule materialisation, budget pace, and
goal projection.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Sum


# ---------------------------------------------------------------------------
# Date helpers (relocated from the deleted pockets app)
# ---------------------------------------------------------------------------


def _clamp_day_to_month(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _shift_month(d: date, delta: int) -> tuple[int, int]:
    total = d.month - 1 + delta
    return d.year + total // 12, total % 12 + 1


def month_start(d: date) -> date:
    return d.replace(day=1)


def month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    last = calendar.monthrange(d.year, d.month)[1]
    return start, d.replace(day=last)


# ---------------------------------------------------------------------------
# Household scoping
# ---------------------------------------------------------------------------


def household_user_ids(user) -> list:
    """User ids the given user can see in a combined view: everyone in their
    household, or just themselves if they aren't in one."""
    from .models import HouseholdMember

    membership = (
        HouseholdMember.objects.filter(user=user).select_related("household").first()
    )
    if membership is None:
        return [user.id]
    return list(
        HouseholdMember.objects.filter(household=membership.household).values_list(
            "user_id", flat=True
        )
    )


def household_members(user) -> list:
    """User objects in the user's household (or just the user)."""
    from .models import HouseholdMember

    membership = HouseholdMember.objects.filter(user=user).first()
    if membership is None:
        return [user]
    return [
        m.user
        for m in HouseholdMember.objects.filter(
            household=membership.household
        ).select_related("user", "user__profile")
    ]


def user_household(user):
    from .models import HouseholdMember

    membership = HouseholdMember.objects.filter(user=user).select_related("household").first()
    return membership.household if membership else None


# ---------------------------------------------------------------------------
# Recurring-rule materialisation
# ---------------------------------------------------------------------------


def compute_next_run(rule, after: date) -> date:
    """The first run date strictly after `after` for `rule`'s cadence."""
    from .models import CADENCE_WEEKLY

    if rule.cadence == CADENCE_WEEKLY:
        return after + timedelta(days=7)
    year, month = _shift_month(after, 1)
    return _clamp_day_to_month(year, month, rule.anchor_day)


def materialize_recurring(as_of: date | None = None) -> int:
    """Create Transactions for every active rule whose next_run has arrived,
    advancing next_run and catching any missed runs. Returns count created."""
    from apps.transactions.models import Transaction

    from .models import RecurringRule

    as_of = as_of or date.today()
    created = 0
    for rule in RecurringRule.objects.filter(active=True, next_run__lte=as_of):
        with db_transaction.atomic():
            run_on = rule.next_run
            while run_on <= as_of:
                Transaction.objects.create(
                    kind=rule.kind,
                    amount=rule.amount,
                    category=rule.category,
                    occurred_on=run_on,
                    notes=rule.notes,
                    owner=rule.owner,
                    recurring_rule=rule,
                )
                created += 1
                run_on = compute_next_run(rule, run_on)
            rule.next_run = run_on
            rule.save(update_fields=["next_run", "updated_at"])
    return created


# ---------------------------------------------------------------------------
# Budget pace
# ---------------------------------------------------------------------------

BUDGET_OVER = "over"
BUDGET_FAST = "fast"
BUDGET_ON_TRACK = "on_track"


def budget_status(user, month: date) -> list:
    """Pace info for every budget the user has in `month` (day-1 date)."""
    from apps.transactions.models import Transaction

    from .models import Budget

    today = date.today()
    start, end = month_bounds(month)
    days_in_month = (end - start).days + 1
    if start <= today <= end:
        days_elapsed = today.day
    elif today > end:
        days_elapsed = days_in_month
    else:
        days_elapsed = 0
    time_ratio = days_elapsed / days_in_month if days_in_month else 0

    rows = []
    budgets = (
        Budget.objects.filter(user=user, month=start)
        .select_related("category")
        .order_by("category__name")
    )
    for b in budgets:
        spent = (
            Transaction.objects.filter(
                owner=user,
                kind="expense",
                category=b.category,
                occurred_on__gte=start,
                occurred_on__lte=end,
            ).aggregate(s=Sum("amount"))["s"]
            or Decimal("0")
        )
        spent = Decimal(spent)
        limit = Decimal(b.limit_amount)
        pace_ratio = float(spent / limit) if limit else 0
        if spent > limit:
            signal = BUDGET_OVER
        elif pace_ratio > time_ratio:
            signal = BUDGET_FAST
        else:
            signal = BUDGET_ON_TRACK
        rows.append(
            {
                "budget": b,
                "category": b.category,
                "limit": limit,
                "spent": spent,
                "remaining": limit - spent,
                "pct": min(100, round(pace_ratio * 100)),
                "pct_raw": round(pace_ratio * 100),
                "time_pct": round(time_ratio * 100),
                "signal": signal,
                "days_elapsed": days_elapsed,
                "days_in_month": days_in_month,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Goal projection
# ---------------------------------------------------------------------------


def goal_status(goal) -> dict:
    target = Decimal(goal.target_amount)
    current = Decimal(goal.current_amount)
    remaining = max(Decimal("0"), target - current)
    pct = float(current / target) if target else 0
    out = {
        "goal": goal,
        "current": current,
        "target": target,
        "remaining": remaining,
        "pct": min(100, round(pct * 100)),
        "complete": current >= target,
        "days_left": None,
        "needed_per_month": None,
        "overdue": False,
    }
    if goal.target_date:
        today = date.today()
        days_left = (goal.target_date - today).days
        out["days_left"] = days_left
        if days_left <= 0:
            out["overdue"] = remaining > 0
        elif remaining > 0:
            months_left = max(1, round(days_left / 30))
            out["needed_per_month"] = (remaining / months_left).quantize(Decimal("1"))
    return out
