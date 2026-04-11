"""Date and time helpers used across the application."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def ensure_datetime(d: date | datetime) -> datetime:
    """Promote a ``date`` to a ``datetime`` at end-of-day if necessary."""
    if isinstance(d, datetime):
        return d
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def business_days_between(start: date, end: date) -> int:
    """Count business days (Mon–Fri) between *start* and *end* inclusive."""
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def date_range(start: date, end: date) -> list[date]:
    """Return a list of calendar dates from *start* to *end* inclusive."""
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days
