"""Forward-looking projections built from already-materialised future
Transaction rows (which RecurringRule generates) plus today's pocket
balances. The key insight: there is no special 'virtual' future row math —
recurring rules pre-create Transactions on their occurrence dates, so
projecting a balance forward is just a running-balance walk over rows
between today and the horizon.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.pockets.models import Pocket
from apps.pockets.permissions import visible_pocket_ids
from apps.reports.services import (
    _ANIMATIONS,
    _AXIS_COLOR,
    _BASE_FONT,
    _BRAND_RAMP,
    _EXPENSE,
    _GRID_COLOR,
    _INCOME,
    _running_balance_at,
)
from apps.transactions.models import (
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_WEEKLY,
    FREQUENCY_YEARLY,
    RecurringRule,
    Transaction,
    Transfer,
)

HORIZON_CHOICES = [
    (3, "Next 3 months"),
    (6, "Next 6 months"),
    (12, "Next 12 months"),
]


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------


@dataclass
class Horizon:
    start: date  # inclusive — usually today
    end: date    # inclusive
    granularity: str  # "day" | "month"
    months: int


def resolve_horizon(months: int) -> Horizon:
    if months not in {3, 6, 12}:
        months = 6
    today = date.today()
    end = _add_months(today, months)
    granularity = "day" if months <= 3 else "month"
    return Horizon(start=today, end=end, granularity=granularity, months=months)


def _add_months(d: date, n: int) -> date:
    """Mirror of apps.transactions.recurring._add_months — kept local to
    avoid pulling in the materialiser."""
    import calendar

    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _all_buckets(horizon: Horizon):
    out: list[date] = []
    if horizon.granularity == "month":
        cur = horizon.start.replace(day=1)
        end = horizon.end.replace(day=1)
        while cur <= end:
            out.append(cur)
            year = cur.year + (1 if cur.month == 12 else 0)
            month = 1 if cur.month == 12 else cur.month + 1
            cur = date(year, month, 1)
    else:
        cur = horizon.start
        while cur <= horizon.end:
            out.append(cur)
            cur += timedelta(days=1)
    return out


def _bucket_key(d: date, granularity: str) -> str:
    return d.strftime("%Y-%m") if granularity == "month" else d.isoformat()


def _bucket_label(d: date, granularity: str) -> str:
    return d.strftime("%b %Y") if granularity == "month" else d.strftime("%d %b")


def scope_pocket_ids(user, pocket_id) -> list:
    if pocket_id:
        try:
            pocket = Pocket.objects.get(pk=pocket_id)
        except Pocket.DoesNotExist:
            return visible_pocket_ids(user)
        return pocket.descendant_ids_with_self()
    return visible_pocket_ids(user)


# ---------------------------------------------------------------------------
# Forecast: balance trajectory
# ---------------------------------------------------------------------------


def forecast_balance_trajectory(user, pocket_ids: list, horizon: Horizon):
    """One series per pocket (capped at 6 for legibility), plotting the
    projected balance from today to horizon.end. Starting balance comes
    from `_running_balance_at(p, today - 1d)`; subsequent buckets add the
    cumulative net effect of Transactions and Transfers in the bucket."""
    pockets = list(
        Pocket.objects.filter(pk__in=pocket_ids)
        .select_related("owner")
        .order_by("name")[:6]
    )
    if not pockets:
        return {"has_data": False, "options": {}}

    buckets = _all_buckets(horizon)
    bucket_keys = [_bucket_key(b, horizon.granularity) for b in buckets]
    bucket_labels = [_bucket_label(b, horizon.granularity) for b in buckets]

    yesterday = horizon.start - timedelta(days=1)

    series = []
    for p in pockets:
        starting = _running_balance_at(p.id, yesterday)

        per_bucket = defaultdict(Decimal)
        # Transactions in the horizon (income +, expense −).
        for row in (
            Transaction.objects.filter(
                pocket_id=p.id,
                occurred_on__gte=horizon.start,
                occurred_on__lte=horizon.end,
            )
            .values("kind", "occurred_on")
            .annotate(total=Sum("amount"))
        ):
            sign = 1 if row["kind"] == "income" else -1
            per_bucket[_bucket_key(row["occurred_on"], horizon.granularity)] += (
                sign * Decimal(row["total"] or 0)
            )
        # Transfers in.
        for row in (
            Transfer.objects.filter(
                to_pocket_id=p.id,
                occurred_on__gte=horizon.start,
                occurred_on__lte=horizon.end,
            )
            .values("occurred_on")
            .annotate(total=Sum("amount"))
        ):
            per_bucket[_bucket_key(row["occurred_on"], horizon.granularity)] += Decimal(
                row["total"] or 0
            )
        # Transfers out.
        for row in (
            Transfer.objects.filter(
                from_pocket_id=p.id,
                occurred_on__gte=horizon.start,
                occurred_on__lte=horizon.end,
            )
            .values("occurred_on")
            .annotate(total=Sum("amount"))
        ):
            per_bucket[_bucket_key(row["occurred_on"], horizon.granularity)] -= Decimal(
                row["total"] or 0
            )

        running = starting
        data = []
        for key in bucket_keys:
            running += per_bucket.get(key, Decimal("0"))
            data.append(int(running))
        series.append({"name": p.name, "data": data})

    return {
        "has_data": True,
        "options": {
            "chart": {
                "type": "area",
                "width": "100%",
                "toolbar": {"show": False},
                "fontFamily": _BASE_FONT,
                "animations": _ANIMATIONS,
            },
            "stroke": {"curve": "smooth", "width": 2},
            "fill": {"type": "gradient", "gradient": {"opacityFrom": 0.45, "opacityTo": 0.08}},
            "dataLabels": {"enabled": False},
            "colors": _BRAND_RAMP[:6],
            "grid": {"borderColor": _GRID_COLOR, "strokeDashArray": 4},
            "legend": {"position": "top", "horizontalAlign": "right", "fontSize": "12px"},
            "xaxis": {
                "categories": bucket_labels,
                "tickAmount": min(len(bucket_labels), 6),
                "labels": {
                    "rotate": -45,
                    "rotateAlways": True,
                    "hideOverlappingLabels": True,
                    "trim": True,
                    "style": {"colors": _AXIS_COLOR, "fontSize": "11px"},
                },
            },
            "yaxis": {"labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "tooltip": {"shared": True, "theme": "light"},
            "series": series,
            "_format": "rupiah",
        },
    }


# ---------------------------------------------------------------------------
# Forecast: monthly net (income vs expense, projected per month)
# ---------------------------------------------------------------------------


def monthly_net_forecast(user, pocket_ids: list, horizon: Horizon):
    """Bar chart with two series, projected income and projected expense per
    month over the horizon. Always month-bucketed regardless of horizon
    granularity — net is a monthly story by nature."""
    today = horizon.start

    income_buckets = defaultdict(Decimal)
    expense_buckets = defaultdict(Decimal)
    for row in (
        Transaction.objects.filter(
            pocket_id__in=pocket_ids,
            occurred_on__gte=today,
            occurred_on__lte=horizon.end,
        )
        .values("kind", "occurred_on")
        .annotate(total=Sum("amount"))
    ):
        key = row["occurred_on"].strftime("%Y-%m")
        if row["kind"] == "income":
            income_buckets[key] += Decimal(row["total"] or 0)
        else:
            expense_buckets[key] += Decimal(row["total"] or 0)

    # Build month buckets explicitly so empty months still render.
    months = []
    cur = today.replace(day=1)
    end = horizon.end.replace(day=1)
    while cur <= end:
        months.append(cur)
        year = cur.year + (1 if cur.month == 12 else 0)
        month = 1 if cur.month == 12 else cur.month + 1
        cur = date(year, month, 1)

    categories = [m.strftime("%b %Y") for m in months]
    income_series = [int(income_buckets[m.strftime("%Y-%m")]) for m in months]
    expense_series = [int(expense_buckets[m.strftime("%Y-%m")]) for m in months]
    has_data = any(income_series) or any(expense_series)

    return {
        "has_data": has_data,
        "options": {
            "chart": {
                "type": "bar",
                "width": "100%",
                "toolbar": {"show": False},
                "fontFamily": _BASE_FONT,
                "animations": _ANIMATIONS,
            },
            "plotOptions": {"bar": {"borderRadius": 6, "columnWidth": "60%"}},
            "colors": [_INCOME, _EXPENSE],
            "dataLabels": {"enabled": False},
            "stroke": {"show": True, "width": 1, "colors": ["transparent"]},
            "grid": {"borderColor": _GRID_COLOR, "strokeDashArray": 4},
            "legend": {"position": "top", "horizontalAlign": "right", "fontSize": "12px"},
            "xaxis": {
                "categories": categories,
                "tickPlacement": "on",
                "labels": {
                    "rotate": -45,
                    "rotateAlways": True,
                    "hideOverlappingLabels": True,
                    "trim": True,
                    "style": {"colors": _AXIS_COLOR, "fontSize": "11px"},
                },
            },
            "yaxis": {"labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "tooltip": {"theme": "light"},
            "series": [
                {"name": "Projected income", "data": income_series},
                {"name": "Projected expense", "data": expense_series},
            ],
            "_format": "rupiah",
        },
    }


# ---------------------------------------------------------------------------
# Active recurring summary (table)
# ---------------------------------------------------------------------------


def active_recurring_summary(user, pocket_ids: list):
    """Active rules currently in scope, with the next upcoming occurrence
    and an approximate monthly equivalent. Skips paused rules."""
    today = date.today()
    rules = (
        RecurringRule.objects.filter(
            created_by=user, is_active=True, pocket_id__in=pocket_ids
        )
        .select_related("pocket", "category")
        .order_by("-kind", "category__name")
    )
    out = []
    for r in rules:
        next_txn = (
            Transaction.objects.filter(recurring_rule=r, occurred_on__gte=today)
            .order_by("occurred_on")
            .first()
        )
        out.append(
            {
                "rule": r,
                "next_on": next_txn.occurred_on if next_txn else None,
                "monthly_equivalent": _monthly_equivalent(r),
            }
        )
    return out


def _monthly_equivalent(rule) -> Decimal:
    """Approximate monthly value of a rule. Used only as a soft summary —
    don't treat as authoritative for anything that affects balance math."""
    amt = Decimal(rule.amount)
    n = Decimal(max(rule.interval, 1))
    if rule.frequency == FREQUENCY_DAILY:
        return amt * Decimal("30") / n
    if rule.frequency == FREQUENCY_WEEKLY:
        return amt * Decimal("4.345") / n
    if rule.frequency == FREQUENCY_MONTHLY:
        return amt / n
    if rule.frequency == FREQUENCY_YEARLY:
        return amt / (Decimal("12") * n)
    return Decimal("0")
