"""Month arithmetic. A month is a 'YYYY-MM' string throughout the package."""

from __future__ import annotations

import calendar
from datetime import date

# Per-article pageview data starts here.
FIRST_AVAILABLE = "2015-07"


def to_ym(month: str) -> tuple[int, int]:
    year, mon = month.split("-")
    return int(year), int(mon)


def from_ym(year: int, mon: int) -> str:
    return f"{year:04d}-{mon:02d}"


def add_months(month: str, n: int) -> str:
    year, mon = to_ym(month)
    index = year * 12 + (mon - 1) + n
    return from_ym(index // 12, index % 12 + 1)


def last_complete_month(today: date) -> str:
    """The month before `today`'s month; the current month is always incomplete."""
    return add_months(from_ym(today.year, today.month), -1)


def month_range(start: str, end: str) -> list[str]:
    months = []
    current = start
    while current <= end:
        months.append(current)
        current = add_months(current, 1)
    return months


def api_start(month: str) -> str:
    """Pageviews API timestamp for the first day of `month`."""
    year, mon = to_ym(month)
    return f"{year:04d}{mon:02d}0100"


def api_end(month: str) -> str:
    """Pageviews API timestamp for the last day of `month` (so the whole month is included)."""
    year, mon = to_ym(month)
    return f"{year:04d}{mon:02d}{calendar.monthrange(year, mon)[1]:02d}00"


def from_api_timestamp(timestamp: str) -> str:
    """'2025010100' -> '2025-01'."""
    return f"{timestamp[:4]}-{timestamp[4:6]}"
