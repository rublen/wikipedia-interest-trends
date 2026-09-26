"""Growth of raw views and of normalized share, previous window vs recent window."""

from __future__ import annotations

PER_MILLION = 1_000_000


def growth_pct(before: float, after: float) -> float | None:
    if before == 0:
        return None
    return round((after / before - 1) * 100, 1)


def share_per_million(article_views: float, project_views: float) -> float | None:
    if project_views == 0:
        return None
    return article_views / project_views * PER_MILLION


def _round_share(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2) if value < 100 else round(value)


def analyze_language(months: list[str], article: dict[str, int], project: dict[str, int]) -> dict:
    """Compare the first half of `months` (previous window) with the second half (recent window)."""
    half = len(months) // 2
    previous, recent = months[:half], months[half:]
    a_prev = sum(article[m] for m in previous)
    a_recent = sum(article[m] for m in recent)
    p_prev = sum(project[m] for m in previous)
    p_recent = sum(project[m] for m in recent)
    s_prev = share_per_million(a_prev, p_prev)
    s_recent = share_per_million(a_recent, p_recent)

    notes = []
    with_data = [m for m in months if article[m] > 0]
    first_with_data = with_data[0] if with_data else None
    if not with_data:
        notes.append("no recorded views in the whole period")
    elif first_with_data > months[0]:
        notes.append(f"no views before {first_with_data} (article may be new or renamed); "
                     "growth may be overstated")
    if a_prev == 0 and a_recent > 0:
        notes.append("no views in the previous window, so growth is undefined")
    missing_totals = [m for m in months if project[m] == 0]
    if missing_totals:
        notes.append(f"project totals missing for {', '.join(missing_totals)}")

    return {
        "views_previous": a_prev,
        "views_recent": a_recent,
        "views_growth_pct": growth_pct(a_prev, a_recent),
        "avg_monthly_views_recent": round(a_recent / len(recent)),
        "share_per_million_previous": _round_share(s_prev),
        "share_per_million_recent": _round_share(s_recent),
        "share_growth_pct": growth_pct(s_prev, s_recent) if s_prev is not None and s_recent is not None else None,
        "project_growth_pct": growth_pct(p_prev, p_recent),
        "first_month_with_data": first_with_data,
        "notes": notes,
    }


def monthly_share(article: dict[str, int], project: dict[str, int]) -> dict[str, float | None]:
    return {m: share_per_million(article[m], project[m]) for m in article}
