"""key_findings are the most-quoted text in agent answers, so each case is tested explicitly."""

from wikitrends import findings, ranking

TOPIC = {"label": "English", "qid": "Q1860", "description": "West Germanic language"}


def lang(views, share_pct, verdict, confidence="high"):
    return {"status": "ok", "avg_monthly_views_recent": views, "share_growth_pct": share_pct,
            "trend": {"verdict": verdict, "confidence": confidence, "reasons": ["r"],
                      "checks": {"noise_pct": 7.0}}}


def run(languages, note=None):
    ranked = ranking.rank(languages, ranking.parse_weights(None))
    return findings.key_findings(TOPIC, languages, ranked, note)


def test_first_finding_names_what_was_analyzed():
    out = run({"de": lang(5000, -0.7, "no_clear_change")}, note="Proxy: the English language article.")
    assert out[0] == ("Analyzing: “English” (Q1860), West Germanic language. "
                      "Proxy: the English language article.")


def test_every_category_is_stated_even_when_empty():
    out = run({"de": lang(5000, -0.7, "no_clear_change"), "ja": lang(9000, -11.0, "declining")})
    assert "Growing: none. Stable (no clear change): de. Declining: ja." in out
    assert "Strongest growth in share: none. Steepest decline in share: ja (fell 11.0%)." in out
    assert "Low confidence, don't rely on these alone: none." in out


def test_ties_name_every_tied_language():
    out = run({"es": lang(5000, -10.4, "declining"), "pl": lang(5000, -10.4, "declining"),
               "de": lang(9000, 12.0, "growing")})
    assert "Largest audience: de (9,000 views/month); smallest: es and pl (5,000 views/month each)." in out
    assert "Strongest growth in share: de (rose 12.0%). Steepest decline in share: es and pl (fell 10.4% each)." in out


def test_single_measurable_language():
    out = run({"cs": lang(183, -47.0, "declining", "medium"), "pl": {"status": "no_article"}})
    assert "Only one language could be measured: cs (183 views/month)." in out
    assert not any(f.startswith("Ranked first") for f in out)  # nothing to rank
    assert out[-1] == "Not measurable (no article or no comparable data): pl."


def test_all_declining():
    out = run({"a": lang(3000, -12.0, "declining"), "b": lang(4000, -20.0, "declining", "low"),
               "c": lang(5000, -30.0, "declining")})
    assert "Growing: none. Stable (no clear change): none. Declining: a, c and b." in out  # ranking order
    assert "Steepest decline in share: c (fell 30.0%)." in " ".join(out)
    assert "Low confidence, don't rely on these alone: b." in out


def test_nothing_measurable():
    out = run({"pl": {"status": "no_article"}})
    assert out[1] == "No language could be measured: none has an article with comparable data."


def test_no_signed_numbers_in_findings():
    out = run({"de": lang(5000, -0.7, "no_clear_change"), "ja": lang(9000, -11.0, "declining"),
               "vi": lang(7000, 1.6, "no_clear_change")})
    assert not any("-" in f.replace("no-", "") for f in out[1:])
