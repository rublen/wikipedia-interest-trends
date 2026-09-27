"""Growth of raw views and of normalized share: last N months vs the same months a year earlier."""

from __future__ import annotations

from wikitrends import trust

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


def analyze_language(months: list[str], article: dict[str, int], project: dict[str, int],
                     lang: str = "this", automated: dict[str, int] | None = None,
                     window: int = trust.YEAR) -> dict:
    """Compare the last `window` months with the same calendar months a year earlier.

    `months` is the whole fetched period (at least window + 12 months); months before the
    compared ones only feed the chart and the trust checks.
    """
    previous, recent = trust.windows(months, window)
    a_prev = sum(article[m] for m in previous)
    a_recent = sum(article[m] for m in recent)
    p_prev = sum(project[m] for m in previous)
    p_recent = sum(project[m] for m in recent)
    s_prev = share_per_million(a_prev, p_prev)
    s_recent = share_per_million(a_recent, p_recent)

    notes = []
    compared = previous + recent
    with_data = [m for m in months if article[m] > 0]
    first_with_data = with_data[0] if with_data else None
    if not with_data:
        notes.append("no recorded views in the whole period")
    elif first_with_data > compared[0]:
        notes.append(f"no views before {first_with_data} (article may be new or renamed); "
                     "growth may be overstated")
    if a_prev == 0 and a_recent > 0:
        notes.append("no views in the year-earlier months, so growth is undefined")
    missing_totals = [m for m in compared if project[m] == 0]
    if missing_totals:
        notes.append(f"project totals missing for {', '.join(missing_totals)}")

    result = {
        "views_previous": a_prev,
        "views_recent": a_recent,
        "views_growth_pct": growth_pct(a_prev, a_recent),
        "avg_monthly_views_recent": round(a_recent / len(recent)),
        "months_compared": len(recent),
        "share_per_million_previous": _round_share(s_prev),
        "share_per_million_recent": _round_share(s_recent),
        "share_growth_pct": growth_pct(s_prev, s_recent) if s_prev is not None and s_recent is not None else None,
        "project_growth_pct": growth_pct(p_prev, p_recent),
        "first_month_with_data": first_with_data,
        "notes": notes,
    }
    trend = trust.assess(months, article, project, result["share_growth_pct"],
                         result["views_growth_pct"], automated, window)
    summary = summarize(lang, result, trend) + " " + trust.sentence(trend)
    return {"summary": summary, "trend": trend, **result}


# Changes smaller than this (in %) are described as "about the same".
UNCHANGED_PCT = 1.0


def change_text(pct: float, up: str = "rose", down: str = "fell") -> str:
    """-8.8 -> 'fell 8.8%'. Signs become words, so a reader can't misread a minus sign."""
    if abs(pct) < UNCHANGED_PCT:
        return "stayed about the same (less than 1% change)"
    return f"{up if pct > 0 else down} {abs(pct):.1f}%"


def share_change_text(share_pct: float, trend: dict) -> str:
    """Model-facing description of the change in share: a direction only if the verdict confirms it."""
    if trend["verdict"] == "no_clear_change":
        return trust.no_change_text(share_pct, trend["checks"].get("noise_pct"))
    return change_text(share_pct)


def summarize(lang: str, r: dict, trend: dict | None = None) -> str:
    """One plain-language interpretation of a language's numbers, written by code, not the agent.

    With a "no_clear_change" verdict the change in share is described by its size relative to
    the noise, without a direction, so the sentence can't be read as growth or decline.
    """
    views, share, project = r["views_growth_pct"], r["share_growth_pct"], r["project_growth_pct"]
    if r["views_recent"] == 0 and r["views_previous"] == 0:
        return "No recorded views in the whole period, so interest can't be measured."
    if views is None or share is None or project is None:
        return "The article had no views in the previous window, so growth can't be computed."

    n = r.get("months_compared", 12)
    text = (f"Article views {change_text(views)} ({r['views_previous']:,} -> {r['views_recent']:,} views "
            f"in total over the {n} compared month{'s' if n > 1 else ''}). "
            f"The whole {lang} Wikipedia {change_text(project, 'grew', 'shrank')} over the same time, "
            f"so the article's share of all views ")
    if trend and trend["verdict"] == "no_clear_change":
        return text + share_change_text(share, trend) + ": no clear change in either direction."
    text += change_text(share)
    if abs(share) < UNCHANGED_PCT:
        return text + ": interest kept pace with the rest of that Wikipedia."
    direction = "gained" if share > 0 else "lost"
    text += f": it {direction} ground relative to the rest of that Wikipedia."
    if views < -UNCHANGED_PCT and share > UNCHANGED_PCT:
        text += " Raw views fell only because the whole Wikipedia shrank faster."
    elif views > UNCHANGED_PCT and share < -UNCHANGED_PCT:
        text += " Raw views rose, but less than the whole Wikipedia grew."
    return text


def _order_key(r: dict) -> tuple[int, float]:
    """Growing (biggest first), then no clear change, then declining (smallest decline first)."""
    verdict = r["trend"]["verdict"]
    if verdict == "no_clear_change":
        return (1, 0.0)
    return (0 if verdict == "growing" else 2, -r["share_growth_pct"])


def comparison(languages: dict[str, dict]) -> str | None:
    """Order languages by change in share, in words (None if fewer than two)."""
    ranked = sorted((lang for lang, r in languages.items()
                     if r.get("share_growth_pct") is not None and r.get("trend")),
                    key=lambda lang: _order_key(languages[lang]))
    if len(ranked) < 2:
        return None
    parts = []
    for lang in ranked:
        r = languages[lang]
        trend = r["trend"]
        parts.append(f"{lang} (share {share_change_text(r['share_growth_pct'], trend)}, "
                     f"{trend['verdict'].replace('_', ' ')} with {trend['confidence']} confidence)")
    return "By change in share of attention, strongest first: " + "; ".join(parts) + "."


def monthly_share(article: dict[str, int], project: dict[str, int]) -> dict[str, float | None]:
    return {m: share_per_million(article[m], project[m]) for m in article}
