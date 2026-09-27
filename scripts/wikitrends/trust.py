"""Trend verdict and confidence from transparent checks.

Comparison: the last `window` complete months vs the same calendar months one year earlier
(year-on-year), so seasonality cancels out. The verdict (growing / declining /
no_clear_change) comes from the change in share of views; each check can cap the
confidence (high -> medium -> low), and every cap comes with a plain-language reason.
"""

from __future__ import annotations

import math
import statistics

# --- thresholds (rules of thumb; see PLAN.md, iteration 2) ------------------
MIN_EFFECT_PCT = 10.0          # smaller changes in share are "no clear change"
NOISE_Z = 2.0                  # change must exceed 2 standard errors of the paired changes
SIGN_TEST_P = 0.025            # one-sided: "this many months in one direction" is unlikely by chance
VOLUME_MEDIUM = 1_000          # avg views/month below this: at most medium
VOLUME_LOW = 100               # below this: low
SPIKE_FACTOR = 3.0             # a month above 3x the typical (median) month is a spike
CONSISTENT_HIGH = 0.80         # share of month pairs moving in the trend's direction
CONSISTENT_MEDIUM = 0.65
SHORT_WINDOW = 6               # fewer compared months: at most medium (too few pairs for a sign test)
BOT_SHARE_MEDIUM = 0.50        # automated share of (user + automated) views; popular articles
                               # often have 20-45% detected bots, so only extreme shares count
COLLAPSE_MIN_AVG = 30          # trailing zero months after this average -> moved/deleted?
BOT_FLAGGING_FROM = "2020-05"  # 'automated' agent exists since April 2020
SHIFT_FACTOR = 3.0             # year-on-year ratio jumps by 3x or more -> abrupt level shift
SHIFT_SPAN = 3                 # months on each side of a level shift
YEAR = 12

LEVELS = ("low", "medium", "high")
# Fixed plain-language meaning of each level, written into the summary so agents quote it
# instead of inventing their own ("weak signal", "real enough to act on", ...).
MEANINGS = {
    "high": "the data consistently shows this; still only a signal of reader interest",
    "medium": "probably real, but weakened by the reasons listed",
    "low": "don't rely on this alone; check the reasons before acting",
}


def windows(months: list[str], window: int) -> tuple[list[str], list[str]]:
    """(previous, recent): the last `window` months and the same calendar months a year earlier."""
    recent = months[-window:]
    previous = months[-window - YEAR:len(months) - YEAR]
    return previous, recent


def _verdict(change_pct: float | None, noise_pct: float | None = None) -> str:
    if change_pct is None:
        return "insufficient_data"
    if abs(change_pct) < MIN_EFFECT_PCT or (noise_pct is not None and abs(change_pct) < noise_pct):
        return "no_clear_change"
    return "growing" if change_pct > 0 else "declining"


def no_change_text(pct: float, noise: float | None) -> str:
    """How much a 'no clear change' moved, relative to the noise, without a direction.

    The direction of a noise-level change means nothing, and showing it ("rose 1.6%")
    made models report growth, so model-facing text gives only the size.
    """
    size = f"moved {abs(pct):.1f}%"
    if noise is not None and abs(pct) < noise:
        return f"{size}, within the ±{noise:.0f}% normal fluctuation"
    if abs(pct) < MIN_EFFECT_PCT:
        return f"{size}, below the {MIN_EFFECT_PCT:g}% needed to count as a real change"
    return f"{size}, too little to count as a clear change"


def _moved(pct: float, decimals: int = 1) -> str:
    """-46.4 -> 'fell 46.4%'. Reasons state directions in words, never with a sign."""
    return f"{'rose' if pct > 0 else 'fell'} {abs(pct):.{decimals}f}%"


def _pct(before: float, after: float) -> float | None:
    return None if before <= 0 else (after / before - 1) * 100


def _noise_pct(prev: list[float], recent: list[float]) -> float | None:
    """Change (in %) that chance alone could produce, from the paired year-on-year changes.

    The spread of the paired log-changes gives a standard error; the noise band is NOISE_Z
    standard errors. Inputs are smoothed shares (never zero).
    """
    if len(prev) < 2:
        return None
    changes = [math.log(r / p) for p, r in zip(prev, recent)]
    se = statistics.stdev(changes) / math.sqrt(len(changes))
    return (math.exp(NOISE_Z * se) - 1) * 100


def _sign_test_significant(agree: int, n: int) -> bool:
    """True if `agree` of `n` coin flips landing the same way has probability < SIGN_TEST_P."""
    if n == 0:
        return False
    p = sum(math.comb(n, k) for k in range(agree, n + 1)) / 2**n
    return p < SIGN_TEST_P


def _level_shift(months: list[str], views: dict[str, float],
                 smoothed: dict[str, float]) -> tuple[str, float, float] | None:
    """Largest abrupt, lasting jump: (month, typical views before, typical views after), or None.

    Works on year-on-year ratios (each month vs the same month a year earlier), so a seasonal
    pattern that repeats every year cancels out. A shift in the recent year and one in the
    year before both show up as a jump in these ratios; the raw data decides which year it was.
    """
    yoy_months = months[YEAR:]
    yoy = {m: smoothed[m] / smoothed[months[i]] for i, m in enumerate(yoy_months)}
    best = None
    for k in range(SHIFT_SPAN, len(yoy_months) - SHIFT_SPAN + 1):
        before = statistics.median(yoy[m] for m in yoy_months[k - SHIFT_SPAN:k])
        after = statistics.median(yoy[m] for m in yoy_months[k:k + SHIFT_SPAN])
        ratio = max(after / before, before / after)
        if ratio >= SHIFT_FACTOR and (best is None or ratio > best[0]):
            best = (ratio, k)
    if best is None:
        return None

    # Which year did the level actually change in? Compare 3-month medians (robust to a single
    # odd month) around the same calendar month in the recent year and the year before.
    k = best[1] + YEAR  # index in `months`

    def levels(j: int) -> tuple[float, float]:
        return (statistics.median(views[m] for m in months[max(0, j - SHIFT_SPAN):j]),
                statistics.median(views[m] for m in months[j:j + SHIFT_SPAN]))

    def size(j: int) -> float:
        before, after = levels(j)
        return max((after + 1) / (before + 1), (before + 1) / (after + 1))

    base = max((k, k - YEAR), key=size)
    before, after = levels(base)
    if before == 0:
        return None  # a new article, reported by its own check
    up = after > before

    # Then pin the month: the biggest single-month step in that direction near `base`.
    def step(j: int) -> float:
        a, b = views[months[j - 1]] + 1, views[months[j]] + 1
        return b / a if up else a / b

    nearby = [j for j in range(base - SHIFT_SPAN + 1, base + SHIFT_SPAN) if 1 <= j < len(months)]
    j = max(nearby, key=step)
    return months[j], *levels(j)


class _Confidence:
    def __init__(self):
        self.level = "high"
        self.lowered: list[str] = []   # reasons that capped the confidence
        self.support: list[str] = []   # reasons that support the verdict

    def cap(self, level: str, reason: str) -> None:
        if LEVELS.index(level) < LEVELS.index(self.level):
            self.level = level
        self.lowered.append(reason)


def assess(months: list[str], article: dict[str, int], project: dict[str, int],
           share_growth_pct: float | None, views_growth_pct: float | None,
           automated: dict[str, int] | None = None, window: int = YEAR) -> dict:
    """months: the whole fetched period (at least window + 12 months), oldest first."""
    prev_m, recent_m = windows(months, window)
    compared = prev_m + recent_m
    n = len(recent_m)
    share = {m: (article[m] / project[m] if project[m] else 0.0) for m in months}
    prev, recent = [share[m] for m in prev_m], [share[m] for m in recent_m]
    conf = _Confidence()
    checks: dict = {}

    with_data = [m for m in compared if article[m] > 0]
    if not with_data or share_growth_pct is None:
        return {"verdict": "insufficient_data", "confidence": "low", "confidence_meaning": MEANINGS["low"],
                "reasons": ["no views in the year-earlier months, so there is nothing to compare against"
                            if with_data else "no recorded views in the compared months"],
                "checks": {}}

    # Verdict: size of the change vs chance. One view is added to every month so empty
    # months don't break the logarithms.
    smoothed = {m: (article[m] + 1) / project[m] if project[m] else None for m in months}
    have_all = all(smoothed[m] for m in compared)
    noise = _noise_pct([smoothed[m] for m in prev_m], [smoothed[m] for m in recent_m]) if have_all else None
    checks["noise_pct"] = None if noise is None else round(noise, 1)
    # A clear majority of months moving one way is also evidence, even if sizes vary a lot.
    # Months equal to their year-earlier value are ties and left out, as in a standard sign test.
    up = share_growth_pct > 0
    moved = [(p, r) for p, r in zip(prev, recent) if r != p]
    agree = sum(1 for p, r in moved if (r > p) == up)
    sign_clear = _sign_test_significant(agree, len(moved))
    verdict = _verdict(share_growth_pct, None if sign_clear else noise)
    if verdict in ("growing", "declining") and noise is not None and abs(share_growth_pct) < noise:
        conf.support.append(f"month-to-month changes vary a lot (±{noise:.0f}%), but {agree} of "
                            f"{len(moved)} changed months moved the same way, which is unlikely by chance")
    elif verdict in ("growing", "declining") and noise is not None:
        conf.support.append(f"the share {_moved(share_growth_pct)}, more than the "
                            f"±{noise:.0f}% that month-to-month variation could produce")
    elif verdict == "no_clear_change":
        conf.support.append(f"the share {no_change_text(share_growth_pct, noise)}")

    if n < SHORT_WINDOW:
        conf.cap("medium", f"only {n} month{'s' if n > 1 else ''} compared with a year earlier; "
                           "short comparisons are easily swayed by one event")

    # 1. Volume: both compared periods need enough views.
    base = min(sum(article[m] for m in prev_m), sum(article[m] for m in recent_m)) / n
    checks["min_avg_monthly_views"] = round(base)
    if base < VOLUME_LOW:
        conf.cap("low", f"about {base:,.0f} views a month is too small a base to trust")
    elif base < VOLUME_MEDIUM:
        conf.cap("medium", f"about {base:,.0f} views a month is a small base")

    # 2. Spikes: does the verdict survive when using medians (typical months) instead of totals?
    typical = statistics.median(share[m] for m in months)
    spikes = [m for m in compared if typical > 0 and share[m] > SPIKE_FACTOR * typical]
    checks["spike_months"] = spikes
    median_change = _pct(statistics.median(prev), statistics.median(recent))
    checks["median_share_growth_pct"] = None if median_change is None else round(median_change, 1)
    median_verdict = _verdict(median_change)
    if verdict in ("growing", "declining") and median_verdict != verdict:
        typical_text = ("typical months show no clear change" if median_verdict in
                        ("no_clear_change", "insufficient_data")
                        else f"typical months moved the other way (they {_moved(median_change, 0)})")
        spike_text = f" (spikes: {', '.join(spikes)})" if spikes else ""
        conf.cap("low", f"the change comes from a few unusual months{spike_text}; {typical_text}")
    elif spikes and verdict in ("growing", "declining"):
        conf.support.append(f"the trend holds for typical months, not just the spike"
                            f"{'s' if len(spikes) > 1 else ''} in {', '.join(spikes)}")

    # 3. Consistency: how many months moved in the verdict's direction vs a year earlier.
    if verdict in ("growing", "declining"):
        frac = agree / n
        checks["months_in_trend_direction"] = f"{agree}/{n}"
        text = f"{agree} of {n} months were {'above' if up else 'below'} the same month a year earlier"
        if frac >= CONSISTENT_HIGH:
            conf.support.append(text)
        elif frac >= CONSISTENT_MEDIUM:
            conf.cap("medium", "only " + text)
        else:
            conf.cap("low", "only " + text + ", so the direction is not consistent")

    # 4. Raw vs share.
    raw_verdict = _verdict(views_growth_pct)
    if verdict in ("growing", "declining") and raw_verdict != verdict:
        conf.cap("medium", f"raw views alone would say {raw_verdict.replace('_', ' ')}; the verdict "
                           "relies on the change in share, i.e. on the whole Wikipedia's traffic change")

    # 6. Artifacts.
    first = with_data[0]
    if first > compared[0]:
        conf.cap("low", f"no views before {first}: the article is probably new or was renamed, "
                        "so the earlier months are not comparable")
    trailing = 0
    for m in reversed(months):
        if article[m] > 0:
            break
        trailing += 1
    earlier = [article[m] for m in months[:len(months) - trailing]]
    if trailing >= 2 and earlier and statistics.fmean(earlier) >= COLLAPSE_MIN_AVG:
        conf.cap("low", f"views dropped to zero for the last {trailing} months: the article may have "
                        "been renamed, merged or deleted")
    if have_all and all(smoothed.values()) and len(months) >= YEAR + 2 * SHIFT_SPAN:
        shift = _level_shift(months, {m: float(article[m]) for m in months}, smoothed)
        if shift:
            month, before, after = shift
            verb = "rose" if after > before else "fell"
            checks["level_shift"] = {"month": month, "views_before": round(before),
                                     "views_after": round(after)}
            since = len(months) - months.index(month)
            text = f"views {verb} abruptly in {month}, from about {before:,.0f} to {after:,.0f} a month"
            if since <= SHIFT_SPAN:
                text += (f"; that was only {since} month{'s' if since > 1 else ''} ago, too recent to tell "
                         "lasting interest from an outside cause (news, a search engine change, bots)")
            else:
                text += ("; jumps this abrupt often have causes outside the topic (search engine changes, "
                         "bots, a rename or redirect), so check the article")
            conf.cap("low", text)
    if automated:
        bot_shares = []
        for period in (prev_m, recent_m):
            user = sum(article[m] for m in period)
            bots = sum(automated.get(m, 0) for m in period)
            bot_shares.append(bots / (user + bots) if user + bots else 0.0)
        worst = max(bot_shares)
        checks["automated_share_max_pct"] = round(worst * 100, 1)
        if worst > BOT_SHARE_MEDIUM:
            conf.cap("medium", f"{worst:.0%} of views in one period came from detected bots; "
                               "undetected bots may also be counted as users")
    if compared[0] < BOT_FLAGGING_FROM:
        conf.cap("medium", "the comparison starts before May 2020, when Wikimedia began flagging "
                           "disguised bots; earlier 'user' views include more bot traffic")
    if any(project[m] == 0 for m in compared):
        conf.cap("medium", "project totals are missing for some months")

    return {
        "verdict": verdict,
        "confidence": conf.level,
        "confidence_meaning": MEANINGS[conf.level],
        "reasons": conf.lowered + conf.support,
        "checks": checks,
    }


def sentence(trend: dict) -> str:
    """'Verdict: declining, with medium confidence (<meaning>). Reasons: <reasons>.'"""
    verdict = trend["verdict"].replace("_", " ")
    reasons = trend["reasons"][:3]
    text = (f"Verdict: {verdict}, with {trend['confidence']} confidence "
            f"({MEANINGS[trend['confidence']]}).")
    return text + (" Reasons: " + "; ".join(reasons) + "." if reasons else "")
