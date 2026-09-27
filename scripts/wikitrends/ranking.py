"""Transparent, user-adjustable ranking of language editions: which audiences to explore next.

score = sum(weight * component). Momentum and size are scaled 0..1 *within the compared
languages*; confidence is already on a fixed 0..1 scale:
- momentum:   change in share of views (higher is better); a change the trust checks call
              "no clear change" counts as 0, so noise can't win the ranking
- size:       average monthly article views, on a log scale (sizes differ 100x between wikis)
- confidence: high = 1, medium = 0.5, low = 0
The score only ranks the languages compared together; it is not an absolute measure.
"""

from __future__ import annotations

import math

from wikitrends import trust

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
    scaled = {"momentum": _scaled(raw["momentum"]), "size": _scaled(raw["size"]),
              "confidence": raw["confidence"]}
    rows = []
    for lang, r in ok.items():
        components = {name: round(scaled[name][lang], 2) for name in raw}
        score = sum(weights[name] * components[name] for name in components)
        trend = r["trend"]
        lowered = [reason for reason in trend["reasons"] if trend["confidence"] != "high"][:1]
        rows.append({
            "lang": lang,
            "score": round(score, 2),
            "components": components,
            "avg_monthly_views": r["avg_monthly_views_recent"],
            "share_growth_pct": r["share_growth_pct"],
            "share_change": _share_change(r),
            "verdict": trend["verdict"],
            "confidence": trend["confidence"],
            "confidence_reason": lowered[0] if lowered else None,
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


def _share_change(r: dict) -> str:
    """The change in share in words; for 'no clear change', its size vs the noise, no direction."""
    pct, trend = r["share_growth_pct"], r["trend"]
    if trend["verdict"] == "no_clear_change":
        return "stable: " + trust.no_change_text(pct, trend["checks"].get("noise_pct"))
    return f"{trend['verdict']}: share {'rose' if pct > 0 else 'fell'} {abs(pct):.1f}%"


def _ordinal(n: int) -> str:
    return {1: "largest", 2: "2nd largest", 3: "3rd largest"}.get(n, f"{n}th largest")


def _why(row: dict, rows: list[dict]) -> str:
    """Why this language has its rank: each component with its value, in words the agent can quote."""
    n = len(rows)
    size_rank = sorted(rows, key=lambda r: r["avg_monthly_views"], reverse=True).index(row) + 1
    c = row["components"]
    size = f"{row['avg_monthly_views']:,} views/month"
    if n > 1:
        size += f", the {_ordinal(size_rank)} audience of {n}"
    confidence = f"{row['confidence']} confidence"
    if row["confidence_reason"]:
        confidence += f" ({row['confidence_reason']})"
    head = f"Ranked {row['rank']} of {n} (score {row['score']:.2f})" if n > 1 else "Only language ranked"
    return (f"{head}: momentum {c['momentum']:.2f}, {row['share_change']}; "
            f"size {c['size']:.2f}, {size}; confidence {c['confidence']:.2f}, {confidence}")


def recommendation(ranking: dict) -> list[str]:
    """Code-written 'what to explore next' lines, framed as next checks, not go/no-go."""
    rows = ranking["languages"]
    if not rows:
        return ["No language could be ranked: none has an article with comparable data."]
    not_measured = ("Not measurable here: " + ", ".join(ranking["not_ranked"])
                    + " (no comparable article data).") if ranking["not_ranked"] else None
    if len(rows) == 1:
        only = rows[0]
        lines = [f"Only {only['lang']} could be measured, so there is nothing to rank. {only['why']}."]
        return lines + ([not_measured] if not_measured else [])
    lines = []
    top = rows[:2] if len(rows) > 2 else rows[:1]
    names = " and ".join(r["lang"] for r in top)
    lines.append(f"Explore next: {names}. " + " ".join(f"{r['lang']}: {r['why']}." for r in top))
    shaky = [r for r in top if r["confidence"] == "low"]
    if shaky:
        lines.append("Check before relying on it: " + ", ".join(r["lang"] for r in shaky)
                     + " ranks high but with low confidence; look at its reasons first.")
    if all(r["verdict"] == "declining" for r in top):
        lines.append("Interest is declining in the top-ranked languages too: the ranking only shows "
                     "where it declines least, not where it grows.")
    rest = rows[len(top):]
    if rest:
        # A plain list: per-language reasons here made the line long, and agents paraphrased
        # long lines instead of quoting them (each language's `why` has the details).
        lines.append(f"Lower priority on this evidence: {', '.join(r['lang'] for r in rest)}.")
    if not_measured:
        lines.append(not_measured)
    lines.append("Audiences here are the readers of each language's Wikipedia, not countries: "
                 "one language is often read in many countries.")
    w = ranking["weights"]
    lines.append(f"Ranking weights: momentum {w['momentum']:g}, size {w['size']:g}, confidence "
                 f"{w['confidence']:g}; momentum and size are scaled 0-1 within these languages, so "
                 "the score only compares them with each other.")
    return lines
