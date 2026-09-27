"""The trust checks on synthetic series with a known right answer."""

import pytest

from wikitrends import analyze, trust
from wikitrends.months import month_range

MONTHS = month_range("2024-09", "2026-08")  # previous window 2024-09..2025-08, recent after
PROJECT = {m: 10_000_000 for m in MONTHS}


def assess(article, automated=None, months=MONTHS, project=None):
    project = project or {m: 10_000_000 for m in months}
    r = analyze.analyze_language(months, article, project, "xx", automated)
    return r["trend"]


def series(prev, recent, months=MONTHS):
    """Per-month values from two lists (or constants) for the previous and recent windows."""
    half = len(months) // 2
    prev = prev if isinstance(prev, list) else [prev] * half
    recent = recent if isinstance(recent, list) else [recent] * half
    return dict(zip(months, prev + recent))


WOBBLE = [1.0, 1.08, 0.95, 1.03, 0.9, 1.1, 0.97, 1.05, 0.92, 1.06, 0.98, 1.02]


def test_steady_growth_is_high_confidence():
    t = assess(series([5000 * w for w in WOBBLE], [6500 * w for w in WOBBLE]))
    assert (t["verdict"], t["confidence"]) == ("growing", "high")
    assert t["checks"]["months_in_trend_direction"] == "12/12"
    assert "the share was higher than in the same month a year earlier in 12 of 12 months" in t["reasons"]


def test_small_change_is_no_clear_change():
    t = assess(series([5000 * w for w in WOBBLE], [5200 * w for w in reversed(WOBBLE)]))
    assert t["verdict"] == "no_clear_change"


def test_single_spike_is_not_a_trend():
    recent = [1000] * 12
    recent[5] = 30_000
    t = assess(series(1000, recent))
    assert t["verdict"] == "growing"          # the totals do grow...
    assert t["confidence"] == "low"           # ...but only because of one month
    assert any("a few unusual months" in r for r in t["reasons"])
    assert t["checks"]["spike_months"] == [MONTHS[17]]


def test_seasonal_peak_is_neither_trend_nor_shift():
    winter = {"11", "12", "01"}
    article = {m: 4000 if m[5:] in winter else 1000 for m in MONTHS}
    t = assess(article)
    assert t["verdict"] == "no_clear_change"
    assert "level_shift" not in t["checks"]


def test_new_article_is_low_confidence():
    t = assess(series([0] * 6 + [2000] * 6, 3000))
    assert t["confidence"] == "low"
    assert any("probably new or was renamed" in r for r in t["reasons"])


@pytest.mark.parametrize("volume, level", [(50, "low"), (500, "medium"), (5000, "high")])
def test_volume_caps_confidence(volume, level):
    t = assess(series([volume * w for w in WOBBLE], [volume * 1.5 * w for w in WOBBLE]))
    assert t["verdict"] == "growing" and t["confidence"] == level


def test_abrupt_level_shift_is_flagged_at_the_right_month():
    recent = [5000] * 6 + [800] * 6          # drops in 2026-03 and stays down
    t = assess(series(5000, recent))
    assert t["verdict"] == "declining" and t["confidence"] == "low"
    assert t["checks"]["level_shift"]["month"] == "2026-03"


def test_uneven_but_consistent_decline_uses_the_sign_test():
    factors = [0.9, 0.2, 0.85, 0.3, 0.95, 0.5, 0.88, 0.25, 0.8, 0.6, 1.1, 0.92]
    t = assess(series(4000, [4000 * f for f in factors]))
    assert t["verdict"] == "declining"
    assert any("unlikely by chance" in r for r in t["reasons"])


def test_heavy_bot_traffic_caps_at_medium():
    article = series([5000 * w for w in WOBBLE], [6500 * w for w in WOBBLE])
    t = assess(article, automated={m: v * 1.5 for m, v in article.items()})
    assert t["confidence"] == "medium"
    assert t["checks"]["automated_share_max_pct"] == 60.0
    assert any("already excluded from these numbers" in r for r in t["reasons"])


def test_period_before_bot_flagging_caps_at_medium():
    months = month_range("2019-01", "2020-12")
    t = assess(series([5000 * w for w in WOBBLE], [6500 * w for w in WOBBLE], months), months=months)
    assert t["confidence"] == "medium"
    assert any("before May 2020" in r for r in t["reasons"])


def test_sentence_puts_lowering_reasons_first():
    trend = {"verdict": "declining", "confidence": "medium",
             "reasons": ["about 500 views a month is a small base", "12 of 12 months were below"]}
    assert trust.sentence(trend) == ("Verdict: declining, with medium confidence (probably real, but "
                                     "weakened by the reasons listed). Reasons: about 500 views a "
                                     "month is a small base; 12 of 12 months were below.")


def test_shift_is_located_despite_a_one_month_dip_a_year_earlier():
    # Shape of Polish "ChatGPT": a one-month dip in the previous year, then a real drop.
    prev = [72_000, 98_000, 75_000, 76_000, 75_000, 27_000, 85_000, 105_000, 97_000, 77_000, 42_000, 23_000]
    recent = [53_000, 71_000, 65_000, 63_000, 53_000, 46_000, 42_000, 14_600, 8_800, 7_100, 5_200, 4_200]
    t = assess(series(prev, recent))
    shift = t["checks"]["level_shift"]
    assert shift["month"] == MONTHS[19]  # the drop, not the recovery from the dip
    assert shift["views_after"] < shift["views_before"]


def test_new_article_is_not_also_reported_as_a_shift():
    t = assess(series([0] * 8 + [150] * 4, 180))
    assert "level_shift" not in t["checks"]
    assert any("probably new" in r for r in t["reasons"])


def test_recent_shift_is_called_too_recent_to_tell():
    t = assess(series(6000, [6000] * 10 + [20_000, 20_000]))  # 3.3x: above SHIFT_FACTOR
    assert t["checks"]["level_shift"]["month"] == MONTHS[-2]
    assert any("too recent to tell" in r for r in t["reasons"])


def test_reasons_state_directions_in_words():
    steady = assess(series([5000 * w for w in WOBBLE], [6500 * w for w in WOBBLE]))
    flat = assess(series([5000 * w for w in WOBBLE], [5200 * w for w in reversed(WOBBLE)]))
    recent = [1000] * 12
    recent[5] = 30_000
    spiky = assess(series(1000, recent))
    for t in (steady, flat, spiky):
        for reason in t["reasons"]:
            assert "(+" not in reason and "(-" not in reason, reason
    assert any(r.startswith("the share rose 30.0%, more than") for r in steady["reasons"])
