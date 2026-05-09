"""Chart data builders for the reports page."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.pockets.models import Pocket
from apps.pockets.permissions import visible_pocket_ids
from apps.transactions.models import Category, Transaction, Transfer


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

PERIOD_CHOICES = [
    ("week", "This week"),
    ("month", "This month"),
    ("quarter", "Last 3 months"),
    ("year", "This year"),
    ("custom", "Custom"),
]


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
# Chart builders
# ---------------------------------------------------------------------------


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


def scope_pocket_ids(user, pocket_id, include_children) -> list:
    if pocket_id:
        try:
            pocket = Pocket.objects.get(pk=pocket_id)
        except Pocket.DoesNotExist:
            return visible_pocket_ids(user)
        if include_children:
            return pocket.descendant_ids_with_self()
        return [pocket.id]
    return visible_pocket_ids(user)


_BASE_FONT = "Inter, sans-serif"
_GRID_COLOR = "#F3D5B5"
_AXIS_COLOR = "#6F4518"
_INCOME = "#5C8A4E"
_EXPENSE = "#9C3D2E"
_BRAND_RAMP = ["#6F4518", "#A47148", "#BC8A5F", "#D4A276", "#E7BC91", "#8B5E34", "#603808", "#583101"]


def income_vs_expense(user, period: Period, pocket_ids: list):
    qs = Transaction.objects.filter(
        pocket_id__in=pocket_ids,
        occurred_on__gte=period.start,
        occurred_on__lte=period.end,
    )
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
            "chart": {"type": "bar", "toolbar": {"show": False}, "fontFamily": _BASE_FONT},
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


def spending_by_category(user, period: Period, pocket_ids: list):
    qs = (
        Transaction.objects.filter(
            kind="expense",
            pocket_id__in=pocket_ids,
            occurred_on__gte=period.start,
            occurred_on__lte=period.end,
        )
        .values("category_id", "category__name", "category__color_token")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:8]
    )
    labels = [r["category__name"] for r in qs]
    series = [int(r["total"] or 0) for r in qs]
    return {
        "has_data": bool(series),
        "options": {
            "chart": {"type": "donut", "fontFamily": _BASE_FONT},
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


def pocket_balances_over_time(user, period: Period, pocket_ids: list):
    """Running balance per pocket over the period. Cumulative from the
    starting balance at period.start."""
    pockets = list(
        Pocket.objects.filter(pk__in=pocket_ids)
        .select_related("owner")
        .order_by("name")
    )

    starting = {}
    for p in pockets:
        starting[p.id] = _running_balance_at(p.id, period.start - timedelta(days=1))

    buckets = _all_buckets(period)
    bucket_keys = [_bucket_key(b, period.granularity) for b in buckets]
    bucket_labels = [_bucket_label(b, period.granularity) for b in buckets]

    series = []
    for p in pockets[:6]:  # cap to 6 series for legibility
        per_bucket_delta = defaultdict(Decimal)
        for row in (
            Transaction.objects.filter(
                pocket_id=p.id,
                occurred_on__gte=period.start,
                occurred_on__lte=period.end,
            )
            .values("kind", "occurred_on")
            .annotate(total=Sum("amount"))
        ):
            sign = 1 if row["kind"] == "income" else -1
            per_bucket_delta[_bucket_key(row["occurred_on"], period.granularity)] += (
                sign * Decimal(row["total"] or 0)
            )
        for row in (
            Transfer.objects.filter(
                to_pocket_id=p.id,
                occurred_on__gte=period.start,
                occurred_on__lte=period.end,
            )
            .values("occurred_on")
            .annotate(total=Sum("amount"))
        ):
            per_bucket_delta[_bucket_key(row["occurred_on"], period.granularity)] += Decimal(
                row["total"] or 0
            )
        for row in (
            Transfer.objects.filter(
                from_pocket_id=p.id,
                occurred_on__gte=period.start,
                occurred_on__lte=period.end,
            )
            .values("occurred_on")
            .annotate(total=Sum("amount"))
        ):
            per_bucket_delta[_bucket_key(row["occurred_on"], period.granularity)] -= Decimal(
                row["total"] or 0
            )

        running = starting[p.id]
        data = []
        for key in bucket_keys:
            running += per_bucket_delta.get(key, Decimal("0"))
            data.append(int(running))
        series.append({"name": p.name, "data": data})

    return {
        "has_data": bool(series),
        "options": {
            "chart": {"type": "area", "toolbar": {"show": False}, "fontFamily": _BASE_FONT},
            "stroke": {"curve": "smooth", "width": 2},
            "fill": {"type": "gradient", "gradient": {"opacityFrom": 0.45, "opacityTo": 0.08}},
            "dataLabels": {"enabled": False},
            "colors": _BRAND_RAMP[:6],
            "grid": {"borderColor": _GRID_COLOR, "strokeDashArray": 4},
            "legend": {"position": "top", "horizontalAlign": "right", "fontSize": "12px"},
            "xaxis": {"categories": bucket_labels, "labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "yaxis": {"labels": {"style": {"colors": _AXIS_COLOR, "fontSize": "11px"}}},
            "tooltip": {"shared": True, "theme": "light"},
            "series": series,
            "_format": "rupiah",
        },
    }


def _running_balance_at(pocket_id, as_of: date) -> Decimal:
    income = Transaction.objects.filter(
        pocket_id=pocket_id, kind="income", occurred_on__lte=as_of
    ).aggregate(s=Sum("amount"))["s"] or 0
    expense = Transaction.objects.filter(
        pocket_id=pocket_id, kind="expense", occurred_on__lte=as_of
    ).aggregate(s=Sum("amount"))["s"] or 0
    transfer_in = Transfer.objects.filter(
        to_pocket_id=pocket_id, occurred_on__lte=as_of
    ).aggregate(s=Sum("amount"))["s"] or 0
    transfer_out = Transfer.objects.filter(
        from_pocket_id=pocket_id, occurred_on__lte=as_of
    ).aggregate(s=Sum("amount"))["s"] or 0
    return Decimal(income) - Decimal(expense) + Decimal(transfer_in) - Decimal(transfer_out)


def top_transactions(user, period: Period, pocket_ids: list, *, n=5):
    qs = (
        Transaction.objects.filter(
            pocket_id__in=pocket_ids,
            occurred_on__gte=period.start,
            occurred_on__lte=period.end,
        )
        .select_related("pocket", "category")
    )
    top_in = list(qs.filter(kind="income").order_by("-amount", "-occurred_on")[:n])
    top_out = list(qs.filter(kind="expense").order_by("-amount", "-occurred_on")[:n])
    return {"top_income": top_in, "top_expense": top_out}
