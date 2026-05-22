"""Chart data builders for the dashboard and reports page.

All builders take `owner_ids` (the people whose ledger to include) plus
optional `source_ids` / `category_id` filters, and return a dict with
`has_data` + ApexCharts `options`. Initial render animates; period-swap
re-renders don't (see `_ANIMATIONS`).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.transactions.models import Transaction


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

PERIOD_CHOICES = [
    ("week", "This week"),
    ("month", "This month"),
    ("last_7", "Last 7 days"),
    ("last_14", "Last 14 days"),
    ("last_30", "Last 30 days"),
    ("quarter", "Last 3 months"),
    ("year", "This year"),
    ("custom", "Custom"),
]


_LAST_N_DAYS = {"last_7": 7, "last_14": 14, "last_30": 30}


@dataclass
class Period:
    start: date
    end: date  # inclusive
    label: str
    granularity: str  # "day" | "month"

    def days(self):
        return (self.end - self.start).days + 1


def resolve_period(period_key: str, start: date | None, end: date | None) -> Period:
    today = date.today()
    if period_key == "custom" and start and end:
        days = (end - start).days + 1
        granularity = "day" if days <= 62 else "month"
        return Period(start, end, f"{start} → {end}", granularity)
    if period_key == "week":
        s = today - timedelta(days=today.weekday())
        return Period(s, s + timedelta(days=6), "This week", "day")
    if period_key in _LAST_N_DAYS:
        n = _LAST_N_DAYS[period_key]
        return Period(today - timedelta(days=n - 1), today, f"Last {n} days", "day")
    if period_key == "quarter":
        s = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        s = (s.replace(day=1) - timedelta(days=1)).replace(day=1)
        return Period(s, today, "Last 3 months", "day" if (today - s).days <= 62 else "month")
    if period_key == "year":
        s = today.replace(month=1, day=1)
        e = today.replace(month=12, day=31)
        return Period(s, e, str(today.year), "month")
    # Default: this month
    s = today.replace(day=1)
    if today.month == 12:
        e = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        e = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return Period(s, e, today.strftime("%B %Y"), "day")


# ---------------------------------------------------------------------------
# Scope + bucket helpers
# ---------------------------------------------------------------------------


def scope_owner_ids(user, person) -> list:
    """Resolve a `person` filter value into a list of owner ids.

    `person` is "me" (default), "household", or a specific user id string.
    """
    from apps.ledger.services import household_user_ids

    if person == "household":
        return household_user_ids(user)
    if person and person != "me":
        try:
            uid = int(person)
        except (TypeError, ValueError):
            return [user.id]
        if uid in household_user_ids(user):
            return [uid]
    return [user.id]


def _bucket_key(d: date, granularity: str) -> str:
    return d.strftime("%Y-%m") if granularity == "month" else d.isoformat()


def _bucket_label(d: date, granularity: str) -> str:
    return d.strftime("%b %Y") if granularity == "month" else d.strftime("%d %b")


def _all_buckets(period: Period):
    out = []
    if period.granularity == "month":
        cur = period.start.replace(day=1)
        end = period.end.replace(day=1)
        while cur <= end:
            out.append(cur)
            year = cur.year + (1 if cur.month == 12 else 0)
            month = 1 if cur.month == 12 else cur.month + 1
            cur = date(year, month, 1)
    else:
        cur = period.start
        while cur <= period.end:
            out.append(cur)
            cur += timedelta(days=1)
    return out


def _bucket_asof(bucket: date, period: Period) -> date:
    """Representative end date for a bucket, clamped to the period end."""
    if period.granularity == "month":
        import calendar

        last = calendar.monthrange(bucket.year, bucket.month)[1]
        end = bucket.replace(day=last)
    else:
        end = bucket
    return min(end, period.end)


_BASE_FONT = "Inter, sans-serif"
_GRID_COLOR = "#F3D5B5"
_AXIS_COLOR = "#6F4518"
_INCOME = "#5C8A4E"
_EXPENSE = "#9C3D2E"
_BRAND_RAMP = ["#6F4518", "#A47148", "#BC8A5F", "#D4A276", "#E7BC91", "#8B5E34", "#603808", "#583101"]

# Initial render animates; period-swap re-renders don't (they happen often).
_ANIMATIONS = {
    "enabled": True,
    "easing": "easeout",
    "speed": 250,
    "animateGradually": {"enabled": False},
    "dynamicAnimation": {"enabled": False},
}


def _scoped(owner_ids, period, *, source_ids=None, category_id=None, kind=None):
    qs = Transaction.objects.filter(
        owner_id__in=owner_ids,
        occurred_on__gte=period.start,
        occurred_on__lte=period.end,
    )
    if kind:
        qs = qs.filter(kind=kind)
    if source_ids:
        qs = qs.filter(source_id__in=source_ids)
    if category_id:
        qs = qs.filter(category_id=category_id)
    return qs


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


def income_vs_expense(period: Period, *, owner_ids, source_ids=None, category_id=None):
    qs = _scoped(owner_ids, period, source_ids=source_ids, category_id=category_id)
    income_buckets = defaultdict(Decimal)
    expense_buckets = defaultdict(Decimal)
    for row in qs.values("kind", "occurred_on").annotate(total=Sum("amount")):
        key = _bucket_key(row["occurred_on"], period.granularity)
        if row["kind"] == "income":
            income_buckets[key] += Decimal(row["total"] or 0)
        else:
            expense_buckets[key] += Decimal(row["total"] or 0)

    buckets = _all_buckets(period)
    categories = [_bucket_label(b, period.granularity) for b in buckets]
    income_series = [int(income_buckets[_bucket_key(b, period.granularity)]) for b in buckets]
    expense_series = [int(expense_buckets[_bucket_key(b, period.granularity)]) for b in buckets]
    has_data = any(income_series) or any(expense_series)
    return {
        "has_data": has_data,
        "options": {
            "chart": {"type": "bar", "toolbar": {"show": False}, "fontFamily": _BASE_FONT, "animations": _ANIMATIONS},
            "plotOptions": {"bar": {"borderRadius": 6, "columnWidth": "60%"}},
            "colors": [_INCOME, _EXPENSE],
            "dataLabels": {"enabled": False},
            "stroke": {"show": True, "width": 1, "colors": ["transparent"]},
            "grid": {"borderColor": _GRID_COLOR, "strokeDashArray": 4},
            "legend": {"position": "top", "horizontalAlign": "right", "fontSize": "12px"},
            "xaxis": {"categories": categories, "labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "yaxis": {"labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "tooltip": {"theme": "light"},
            "series": [
                {"name": "Income", "data": income_series},
                {"name": "Expense", "data": expense_series},
            ],
            "_format": "rupiah",
        },
    }


def spending_by_category(period: Period, *, owner_ids, source_ids=None):
    qs = (
        _scoped(owner_ids, period, source_ids=source_ids, kind="expense")
        .values("category_id", "category__name", "category__color_token")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:8]
    )
    labels = [r["category__name"] for r in qs]
    series = [int(r["total"] or 0) for r in qs]
    return {
        "has_data": bool(series),
        "options": {
            "chart": {"type": "donut", "fontFamily": _BASE_FONT, "animations": _ANIMATIONS},
            "labels": labels,
            "series": series,
            "colors": _BRAND_RAMP,
            "dataLabels": {"enabled": False},
            "legend": {"position": "bottom", "fontSize": "12px", "labels": {"colors": "#583101"}},
            "stroke": {"width": 2, "colors": ["#FFFFFF"]},
            "plotOptions": {"pie": {"donut": {"size": "62%"}}},
            "tooltip": {},
            "_format": "rupiah",
        },
    }


def source_breakdown(period: Period, *, owner_ids, kind="expense"):
    qs = (
        _scoped(owner_ids, period, kind=kind)
        .values("source__name", "source__color_token")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    labels = [(r["source__name"] or "No source") for r in qs]
    series = [int(r["total"] or 0) for r in qs]
    return {
        "has_data": bool(series),
        "options": {
            "chart": {"type": "donut", "fontFamily": _BASE_FONT, "animations": _ANIMATIONS},
            "labels": labels,
            "series": series,
            "colors": _BRAND_RAMP,
            "dataLabels": {"enabled": False},
            "legend": {"position": "bottom", "fontSize": "12px", "labels": {"colors": "#583101"}},
            "stroke": {"width": 2, "colors": ["#FFFFFF"]},
            "plotOptions": {"pie": {"donut": {"size": "62%"}}},
            "tooltip": {},
            "_format": "rupiah",
        },
    }


def net_worth_over_time(period: Period, *, user_ids, series_name="Net worth"):
    """Combined balance across `user_ids` over the period, fed by daily
    snapshots. For each bucket we carry forward the latest snapshot on/before
    the bucket's end date and sum across members."""
    from apps.ledger.models import DailyBalanceSnapshot

    snaps = (
        DailyBalanceSnapshot.objects.filter(
            user_id__in=user_ids, on_date__lte=period.end
        )
        .order_by("user_id", "on_date")
        .values_list("user_id", "on_date", "balance")
    )
    by_user = defaultdict(list)
    for uid, on_date, balance in snaps:
        by_user[uid].append((on_date, Decimal(balance)))

    def balance_as_of(rows, as_of):
        val = Decimal("0")
        for d, b in rows:
            if d <= as_of:
                val = b
            else:
                break
        return val

    buckets = _all_buckets(period)
    labels = [_bucket_label(b, period.granularity) for b in buckets]
    data = []
    for b in buckets:
        as_of = _bucket_asof(b, period)
        total = sum((balance_as_of(by_user.get(uid, []), as_of) for uid in user_ids), Decimal("0"))
        data.append(int(total))

    has_data = bool(snaps) and any(data)
    return {
        "has_data": has_data,
        "options": {
            "chart": {"type": "area", "toolbar": {"show": False}, "fontFamily": _BASE_FONT, "animations": _ANIMATIONS},
            "stroke": {"curve": "smooth", "width": 2},
            "fill": {"type": "gradient", "gradient": {"opacityFrom": 0.45, "opacityTo": 0.08}},
            "dataLabels": {"enabled": False},
            "colors": [_BRAND_RAMP[0]],
            "grid": {"borderColor": _GRID_COLOR, "strokeDashArray": 4},
            "legend": {"show": False},
            "xaxis": {"categories": labels, "labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "yaxis": {"labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "tooltip": {"theme": "light"},
            "series": [{"name": series_name, "data": data}],
            "_format": "rupiah",
        },
    }


def top_transactions(period: Period, *, owner_ids, source_ids=None, category_id=None, n=5):
    qs = _scoped(owner_ids, period, source_ids=source_ids, category_id=category_id).select_related(
        "source", "category", "owner", "owner__profile"
    )
    top_in = list(qs.filter(kind="income").order_by("-amount", "-occurred_on")[:n])
    top_out = list(qs.filter(kind="expense").order_by("-amount", "-occurred_on")[:n])
    return {"top_income": top_in, "top_expense": top_out}
