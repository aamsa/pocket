"""Materialisation helpers for RecurringRule.

`compute_occurrences` is a pure date-math function. `materialize` and
`clear_future` are the two side-effecting operations the views use to
keep the Transaction table in sync with a rule.
"""

import calendar
from datetime import date, timedelta

from .models import (
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_WEEKLY,
    FREQUENCY_YEARLY,
    Transaction,
)


def _add_months(d: date, n: int) -> date:
    """Add n months to d, clamping to the last valid day of the target month
    (so Jan 31 + 1 month becomes Feb 28 / 29, not an invalid date)."""
    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(d: date, n: int) -> date:
    """Add n years to d, clamping Feb 29 to Feb 28 in non-leap years."""
    year = d.year + n
    try:
        return d.replace(year=year)
    except ValueError:
        return d.replace(year=year, day=28)


def compute_occurrences(
    *,
    start_date: date,
    frequency: str,
    interval: int,
    end_date: date | None,
    occurrences: int | None,
) -> list[date]:
    """Compute every occurrence date for a rule. Stops at whichever limit
    fires first: end_date inclusive, or `occurrences` count.

    Caller must supply at least one of end_date / occurrences — the model
    constraint `recurring_bounded` enforces this. We still hard-cap iterations
    to 1000 as a defensive guard against infinite loops.
    """
    if interval < 1:
        interval = 1
    out: list[date] = []
    d = start_date
    cap = occurrences if occurrences is not None else 1000

    for i in range(cap):
        if end_date is not None and d > end_date:
            break
        out.append(d)

        if frequency == FREQUENCY_DAILY:
            d = d + timedelta(days=interval)
        elif frequency == FREQUENCY_WEEKLY:
            d = d + timedelta(weeks=interval)
        elif frequency == FREQUENCY_MONTHLY:
            d = _add_months(start_date, (i + 1) * interval)
        elif frequency == FREQUENCY_YEARLY:
            d = _add_years(start_date, (i + 1) * interval)
        else:
            break

    return out


def materialize(rule, *, from_date: date | None = None) -> int:
    """Create Transaction rows for every occurrence on or after `from_date`.

    Idempotent: uses get_or_create keyed on (recurring_rule, occurred_on),
    so calling materialize twice is safe.

    Returns the number of rows actually created."""
    if not rule.is_active:
        return 0

    occurrences = compute_occurrences(
        start_date=rule.start_date,
        frequency=rule.frequency,
        interval=rule.interval,
        end_date=rule.end_date,
        occurrences=rule.occurrences,
    )
    cutoff = from_date or rule.start_date
    created = 0
    for occurred_on in occurrences:
        if occurred_on < cutoff:
            continue
        _, was_created = Transaction.objects.get_or_create(
            recurring_rule=rule,
            occurred_on=occurred_on,
            defaults={
                "pocket": rule.pocket,
                "kind": rule.kind,
                "amount": rule.amount,
                "category": rule.category,
                "notes": rule.notes,
                "created_by": rule.created_by,
            },
        )
        if was_created:
            created += 1
    return created


def clear_future(rule, *, from_date: date | None = None) -> int:
    """Delete Transaction rows generated from this rule whose occurred_on is
    on or after `from_date` (default: today). Past rows are left in place
    so the historical ledger stays accurate.

    Returns the number of rows deleted."""
    cutoff = from_date or date.today()
    deleted, _ = Transaction.objects.filter(
        recurring_rule=rule, occurred_on__gte=cutoff
    ).delete()
    return deleted
