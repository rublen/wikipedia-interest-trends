import json
import re
from datetime import date

import pytest

from fakes import FakeClient, entity, many_sites
from wikitrends import pipeline, ranking, report
from wikitrends.months import month_range
from wikitrends.resolve import resolve


def lang_result(views, share_pct, verdict, confidence="high", reasons=("a reason",)):
    return {"status": "ok", "avg_monthly_views_recent": views, "share_growth_pct": share_pct,
            "trend": {"verdict": verdict, "confidence": confidence, "reasons": list(reasons),
                      "checks": {"noise_pct": 7.0}}}


def test_weights_default_custom_and_errors():
    assert ranking.parse_weights(None) == {"momentum": 0.4, "size": 0.4, "confidence": 0.2}
    assert ranking.parse_weights("momentum=2,size=1,confidence=1") == {"momentum": 0.5, "size": 0.25,
                                                                        "confidence": 0.25}
    for bad, message in [("speed=1", "unknown weight"), ("size=x", "must be a number"),
                         ("size=-1", "must not be negative"), ("momentum=0,size=0,confidence=0", "positive")]:
        with pytest.raises(ranking.WeightsError, match=message):
            ranking.parse_weights(bad)


def test_noise_level_change_does_not_count_as_momentum():
    langs = {"vi": lang_result(12_000, 1.6, "no_clear_change"),
             "tr": lang_result(12_000, -0.2, "no_clear_change"),
             "ja": lang_result(12_000, -11.0, "declining")}
    rows = {r["lang"]: r for r in ranking.rank(langs, ranking.parse_weights(None))["languages"]}
    assert rows["vi"]["components"]["momentum"] == rows["tr"]["components"]["momentum"] == 1.0
    assert rows["ja"]["components"]["momentum"] == 0.0
    assert "stable: moved 1.6%, within the ±7% normal fluctuation" in rows["vi"]["why"]
    assert "rose" not in rows["vi"]["why"]


def test_ranking_order_explanations_and_not_ranked():
    langs = {"de": lang_result(23_000, -0.7, "no_clear_change", "medium", reasons=("bots",)),
             "ja": lang_result(36_000, -11.0, "declining"),
             "uk": lang_result(6_600, -14.6, "declining"),
             "pl": {"status": "no_article", "note": "long note"}}
    result = ranking.rank(langs, ranking.parse_weights(None))
    assert [r["lang"] for r in result["languages"]] == ["de", "ja", "uk"]
    assert result["languages"][0]["why"] == (
        "Ranked 1 of 3 (score 0.80): momentum 1.00, stable: moved 0.7%, within the ±7% normal "
        "fluctuation; size 0.74, 23,000 views/month, the 2nd largest audience of 3; "
        "confidence 0.50, medium confidence (bots)")
    assert "36,000 views/month, the largest audience of 3" in result["languages"][1]["why"]
    assert result["not_ranked"] == {"pl": "no article on this topic in this Wikipedia"}
    # Size-only weights put the biggest audience first.
    by_size = ranking.rank(langs, ranking.parse_weights("momentum=0,size=1,confidence=0"))
    assert by_size["languages"][0]["lang"] == "ja"


def test_recommendation_cases():
    single = ranking.rank({"cs": lang_result(183, -47.0, "declining", "medium"),
                           "pl": {"status": "no_article"}}, ranking.parse_weights(None))
    lines = ranking.recommendation(single)
    assert lines[0].startswith("Only cs could be measured, so there is nothing to rank")
    assert lines[1].startswith("Not measurable here: pl")
    assert not any(line.startswith("Ranking weights") for line in lines)  # nothing was ranked

    declining = ranking.rank({"a": lang_result(5000, -12.0, "declining"),
                              "b": lang_result(4000, -20.0, "declining", "low"),
                              "c": lang_result(3000, -30.0, "declining")}, ranking.parse_weights(None))
    lines = ranking.recommendation(declining)
    assert lines[0].startswith("Explore next: a and b.")
    assert any(line.startswith("Check before relying on it: b") for line in lines)
    assert any("only shows where it declines least" in line for line in lines)
    assert "Lower priority on this evidence: c." in lines
    assert any(line.startswith("Audiences here are the readers of each language's Wikipedia, not countries")
               for line in lines)
    assert lines[-1].startswith("Ranking weights: momentum 0.4, size 0.4, confidence 0.2")


# --- report ------------------------------------------------------------------

MONTHS = month_range("2024-09", "2026-08")
LANGS = ["uk", "pl", "de", "es", "pt", "tr", "ja", "vi"]


def _client(langs):
    sites = {f"{lang}wiki": f"English-{lang}" for lang in langs}
    return FakeClient(
        search={"english": [{"id": "Q1860", "label": "English", "description": "language"}]},
        entities={"Q1860": entity("English", "West Germanic language", many_sites(10, sites))},
        articles={(lang, f"English-{lang}"): {m: 1000 * (i + 1) + 10 * j for j, m in enumerate(MONTHS)}
                  for i, lang in enumerate(langs)},
        projects={lang: {m: 50_000_000 for m in MONTHS} for lang in langs},
    )


def _pdf_pages(path):
    return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))


@pytest.mark.parametrize("langs", [LANGS[:2], LANGS])
def test_report_is_one_page_and_fits(tmp_path, langs):
    client = _client(langs)
    resolved = resolve(client, langs, topic="english")
    spec = pipeline.build_spec(client, resolved, "english", langs, 24, date(2026, 9, 25))
    result = pipeline.analyze_spec(client, spec, tmp_path, make_report=True,
                                   question="Which audiences should we explore next?", note="Proxy: …")
    pdf = tmp_path / "report.pdf"
    assert result["files"]["report"] == str(pdf) and pdf.exists()
    assert _pdf_pages(pdf) == 1
    assert not any("did not fit" in n or "not everything fit" in n for n in result["period"]["notes"])
    assert result["recommendation"] and result["ranking"]["languages"]


def test_no_report_unless_asked(tmp_path):
    client = _client(LANGS[:2])
    resolved = resolve(client, LANGS[:2], topic="english")
    spec = pipeline.build_spec(client, resolved, "english", LANGS[:2], 24, date(2026, 9, 25))
    result = pipeline.analyze_spec(client, spec, tmp_path)
    assert "report" not in result["files"] and not (tmp_path / "report.pdf").exists()


def test_unrenderable_titles_are_detected():
    assert report.renderable("Englische Sprache Англійська мова")
    assert not report.renderable("\U000F0000")  # private-use character: no font has it


def test_model_facing_result_has_no_signed_numbers(tmp_path):
    client = _client(LANGS[:3])
    resolved = resolve(client, LANGS[:3], topic="english")
    spec = pipeline.build_spec(client, resolved, "english", LANGS[:3], 24, date(2026, 9, 25))
    result = pipeline.analyze_spec(client, spec, tmp_path, make_report=True, note="Proxy: X")
    text = (tmp_path / "result.json").read_text()
    assert "_growth_pct" not in text
    assert not re.search(r"[(\s]-\d", text), "a negative number reached the model-facing JSON"
    assert result["topic"]["note"] == "Proxy: X"
    # Human-facing CSV keeps the raw numbers.
    assert (tmp_path / "monthly.csv").read_text().startswith("month,lang,article_views")


def test_many_languages_get_compact_output_unless_details(tmp_path):
    client = _client(LANGS[:4])
    resolved = resolve(client, LANGS[:4], topic="english")
    spec = pipeline.build_spec(client, resolved, "english", LANGS[:4], 24, date(2026, 9, 25))
    out = pipeline.analyze_spec(client, spec, tmp_path)
    assert set(out["languages"]["uk"]) == {"status", "title", "line"}
    assert "summary" not in json.dumps(out) and out["details"].startswith("Compact output")
    assert list(out)[:5] == ["status", "topic", "key_findings", "period", "comparison"]
    # result.json keeps the full agent-facing detail; --details prints it.
    assert "summary" in json.loads((tmp_path / "result.json").read_text())["languages"]["uk"]
    full = pipeline.analyze_spec(client, spec, tmp_path, details=True)
    assert "summary" in full["languages"]["uk"]


def test_two_languages_keep_full_output(tmp_path):
    client = _client(LANGS[:2])
    resolved = resolve(client, LANGS[:2], topic="english")
    spec = pipeline.build_spec(client, resolved, "english", LANGS[:2], 24, date(2026, 9, 25))
    out = pipeline.analyze_spec(client, spec, tmp_path)
    assert "summary" in out["languages"]["uk"] and "details" not in out
