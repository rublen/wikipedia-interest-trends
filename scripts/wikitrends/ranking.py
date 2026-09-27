"""Transparent, user-adjustable ranking of language editions: which audiences to explore next.

score = sum(weight * component), each component scaled 0..1 *within the compared languages*:
- momentum:   change in share of views (higher is better); a change the trust checks call
              "no clear change" counts as 0, so noise can't win the ranking
- size:       average monthly article views, on a log scale (sizes differ 100x between wikis)
- confidence: high = 1, medium = 0.5, low = 0
The score only ranks the languages compared together; it is not an absolute measure.
"""

from __future__ import annotations

import math

DEFAULT_WEIGHTS = {"momentum": 0.4, "size": 0.4, "confidence": 0.2}
CONFIDENCE_VALUE = {"high": 1.0, "medium": 0.5, "low": 0.0}


class WeightsError(ValueError):
    """--weights could not be parsed."""


def parse_weights(text: str | None) -> dict[str, float]:
    """'momentum=0.5,size=0.3' -> weights (missing ones keep defaults), normalized to sum 1."""
    weights = dict(DEFAULT_WEIGHTS)
    if text:
        for part in text.split(","):
            name, _, value = part.partition("=")
            name = name.strip()
            if name not in weights:
                raise WeightsError(f"unknown weight '{name}'; use {', '.join(DEFAULT_WEIGHTS)}")
            try:
                weights[name] = float(value)
            except ValueError:
                raise WeightsError(f"weight '{name}' must be a number, got '{value}'") from None
            if weights[name] < 0:
                raise WeightsError(f"weight '{name}' must not be negative")
    total = sum(weights.values())
    if total <= 0:
        raise WeightsError("at least one weight must be positive")
    return {k: round(v / total, 3) for k, v in weights.items()}


def _scaled(values: dict[str, float]) -> dict[str, float]:
    """Min-max scale to 0..1; if all values are equal, everyone gets 0.5."""
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def rank(languages: dict[str, dict], weights: dict[str, float]) -> dict:
    """Score the analyzable languages; list the rest as not ranked, with the reason."""
    ok = {lang: r for lang, r in languages.items()
          if r.get("status") == "ok" and r.get("share_growth_pct") is not None}
    not_ranked = {lang: _not_ranked_reason(r) for lang, r in languages.items() if lang not in ok}
    if not ok:
        return {"weights": weights, "languages": [], "not_ranked": not_ranked}

    raw = {
        "momentum": {lang: _momentum(r) for lang, r in ok.items()},
        "size": {lang: math.log10(max(r["avg_monthly_views_recent"], 1)) for lang, r in ok.items()},
        "confidence": {lang: CONFIDENCE_VALUE[r["trend"]["confidence"]] for lang, r in ok.items()},
    }
    scaled = {name: _scaled(values) for name, values in raw.items()}
    rows = []
    for lang, r in ok.items():
        components = {name: round(scaled[name][lang], 2) for name in raw}
        score = sum(weights[name] * components[name] for name in components)
        rows.append({
            "lang": lang,
            "score": round(score, 2),
            "components": components,
            "avg_monthly_views": r["avg_monthly_views_recent"],
            "share_growth_pct": r["share_growth_pct"],
            "verdict": r["trend"]["verdict"],
            "confidence": r["trend"]["confidence"],
        })
    rows.sort(key=lambda row: row["score"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
        row["why"] = _why(row, rows)
    return {"weights": weights, "languages": rows, "not_ranked": not_ranked}


def _not_ranked_reason(r: dict) -> str:
    return {"no_article": "no article on this topic in this Wikipedia",
            "unknown_language": "unknown language code"}.get(r.get("status"), "growth can't be computed "
                                                                              "(no views a year earlier)")


def _momentum(r: dict) -> float:
    """Change in share, counted only when the trust checks confirm it."""
    return r["share_growth_pct"] if r["trend"]["verdict"] in ("growing", "declining") else 0.0


def _why(row: dict, rows: list[dict]) -> str:
    """Plain-language reasons for one language's position, relative to the group."""
    parts = []
    n = len(rows)
    by_size = sorted(rows, key=lambda r: r["avg_monthly_views"], reverse=True)
    views = f"{row['avg_monthly_views']:,} views/month"
    if n > 1 and by_size[0] is row:
        parts.append(f"largest audience in the group ({views})")
    elif n > 1 and by_size[-1] is row:
        parts.append(f"smallest audience in the group ({views})")
    else:
        parts.append(f"audience of {views}")
    change = row["share_growth_pct"]
    moved = f"share {'rose' if change > 0 else 'fell'} {abs(change):.1f}%"
    if row["verdict"] == "no_clear_change":
        parts.append(f"stable ({moved}, not a clear change)")
    else:
        parts.append(f"{row['verdict']} ({moved})")
    parts.append(f"{row['confidence']} confidence")
    return "; ".join(parts)


def recommendation(ranking: dict) -> list[str]:
    """Code-written 'what to explore next' lines, framed as next checks, not go/no-go."""
    rows = ranking["languages"]
    if not rows:
        return ["No language could be ranked: none has an article with comparable data."]
    not_measured = ("Not measurable here: " + ", ".join(ranking["not_ranked"])
                    + " (no comparable article data).") if ranking["not_ranked"] else None
    if len(rows) == 1:
        only = rows[0]
        lines = [f"Only {only['lang']} could be measured, so there is nothing to rank: {only['why']}."]
        return lines + ([not_measured] if not_measured else [])
    lines = []
    top = rows[:2] if len(rows) > 2 else rows[:1]
    names = " and ".join(r["lang"] for r in top)
    lines.append(f"Explore next: {names}. " + " ".join(
        f"{r['lang']}: {r['why']}." for r in top))
    shaky = [r for r in top if r["confidence"] == "low"]
    if shaky:
        lines.append("Check before relying on it: " + ", ".join(r["lang"] for r in shaky)
                     + " ranks high but with low confidence; look at its reasons first.")
    if all(r["verdict"] == "declining" for r in top):
        lines.append("Interest is declining in the top-ranked languages too: the ranking only shows "
                     "where it declines least, not where it grows.")
    rest = [r["lang"] for r in rows[len(top):]]
    if rest:
        lines.append(f"Lower priority on this evidence: {', '.join(rest)}.")
    if not_measured:
        lines.append(not_measured)
    return lines
