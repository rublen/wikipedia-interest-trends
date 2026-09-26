import json
from datetime import date

import pytest
import requests

from fakes import FakeClient, entity, many_sites
from wikitrends import analyze, pipeline
from wikitrends.api import ApiError, Client, NotFound
from wikitrends.config import user_agent
from wikitrends.months import add_months, api_end, api_start, last_complete_month, month_range
from wikitrends.resolve import resolve

MONTHS_24 = month_range("2024-09", "2026-08")


# --- months -----------------------------------------------------------------

def test_month_arithmetic():
    assert add_months("2025-12", 1) == "2026-01"
    assert add_months("2025-01", -1) == "2024-12"
    assert last_complete_month(date(2026, 9, 25)) == "2026-08"
    assert last_complete_month(date(2026, 1, 1)) == "2025-12"
    assert len(MONTHS_24) == 24


def test_api_timestamps_cover_whole_months():
    assert api_start("2024-02") == "2024020100"
    assert api_end("2024-02") == "2024022900"  # leap year
    assert api_end("2026-08") == "2026083100"


# --- analysis ---------------------------------------------------------------

def test_share_normalization_separates_topic_from_wiki_traffic():
    # Article +5% while the whole wiki drops 12.5%: raw looks flat, share clearly grows.
    article = {m: (100 if i < 12 else 105) for i, m in enumerate(MONTHS_24)}
    project = {m: (8_000_000 if i < 12 else 7_000_000) for i, m in enumerate(MONTHS_24)}
    r = analyze.analyze_language(MONTHS_24, article, project)
    assert r["views_previous"] == 1200 and r["views_recent"] == 1260
    assert r["views_growth_pct"] == 5.0
    assert r["project_growth_pct"] == -12.5
    assert r["share_growth_pct"] == 20.0
    assert r["share_per_million_previous"] == 12.5
    assert r["notes"] == []


def test_new_article_is_flagged():
    article = {m: (0 if i < 6 else 50) for i, m in enumerate(MONTHS_24)}
    project = {m: 1_000_000 for m in MONTHS_24}
    r = analyze.analyze_language(MONTHS_24, article, project)
    assert r["first_month_with_data"] == "2025-03"
    assert any("no views before 2025-03" in n for n in r["notes"])


def test_growth_undefined_without_previous_views():
    article = {m: (0 if i < 12 else 10) for i, m in enumerate(MONTHS_24)}
    project = {m: 1_000_000 for m in MONTHS_24}
    r = analyze.analyze_language(MONTHS_24, article, project)
    assert r["views_growth_pct"] is None and r["share_growth_pct"] is None
    assert any("growth is undefined" in n for n in r["notes"])


# --- resolve ----------------------------------------------------------------

def _mercury_like_client(top_hit_is_most_linked: bool, ratio: float) -> FakeClient:
    best, other = 200, int(200 / ratio)
    hits = [{"id": "Q1", "label": "A", "description": "a"}, {"id": "Q2", "label": "B", "description": "b"}]
    entities = {
        "Q1": entity("A", "a", many_sites(best if top_hit_is_most_linked else other, {"plwiki": "A-pl"})),
        "Q2": entity("B", "b", many_sites(other if top_hit_is_most_linked else best)),
    }
    return FakeClient(search={"topic": hits}, entities=entities)


def test_resolve_autopicks_dominant_top_hit():
    r = resolve(_mercury_like_client(True, ratio=3), ["pl", "cs"], topic="topic")
    assert r["status"] == "resolved"
    assert r["item"]["qid"] == "Q1"
    assert r["titles"] == {"pl": "A-pl", "cs": None}
    res = r["resolution"]
    assert res["decision"] == "auto_picked" and res["ratio"] == round(201 / 66, 2)  # 200 + plwiki vs int(200/3)
    assert (res["best"]["qid"], res["runner_up"]["qid"]) == ("Q1", "Q2")
    assert [c["search_rank"] for c in res["candidates"]] == [1, 2]


@pytest.mark.parametrize("top_is_best, ratio", [(True, 1.5), (False, 3)])
def test_resolve_ambiguous_returns_candidates(top_is_best, ratio):
    r = resolve(_mercury_like_client(top_is_best, ratio), ["pl"], topic="topic")
    assert r["status"] == "ambiguous"
    res = r["resolution"]
    assert res["decision"] == "ambiguous" and len(res["candidates"]) == 2
    assert res["best"]["wikipedias"] >= res["runner_up"]["wikipedias"]
    expected = "is not the most-linked item" if not top_is_best else "2x required"
    assert expected in res["reason"]


def test_sister_projects_are_not_counted_as_wikipedias():
    # 'abstractwiki' looks like a language Wikipedia id but is Abstract Wikipedia.
    client = FakeClient(entities={"Q9": entity("X", "x", {"ukwiki": "Ікс", "abstractwiki": "X",
                                                          "commonswiki": "X"})})
    assert resolve(client, ["uk"], qid="Q9")["item"]["wikipedias"] == 1


def test_resolve_by_qid_and_not_found():
    client = FakeClient(entities={"Q9": entity("X", "x", {"ukwiki": "Ікс"})})
    assert resolve(client, ["uk"], qid="Q9")["titles"] == {"uk": "Ікс"}
    assert resolve(client, ["uk"], qid="Q404")["status"] == "not_found"
    assert resolve(client, ["uk"], topic="nothing")["status"] == "not_found"


def test_disambiguation_pages_are_ignored():
    hits = [{"id": "Q5", "label": "M", "description": "Wikimedia disambiguation page"},
            {"id": "Q6", "label": "M", "description": "real thing"}]
    client = FakeClient(search={"m": hits}, entities={"Q6": entity("M", "real thing", many_sites(10))})
    assert resolve(client, ["en"], topic="m")["item"]["qid"] == "Q6"


# --- pipeline ---------------------------------------------------------------

def _fasting_client() -> FakeClient:
    return FakeClient(
        search={"fasting": [{"id": "Q1666254", "label": "intermittent fasting", "description": "diet"}]},
        entities={"Q1666254": entity("intermittent fasting", "diet",
                                     many_sites(30, {"cswiki": "Přerušovaný půst"}))},
        articles={("cs", "P%C5%99eru%C5%A1ovan%C3%BD_p%C5%AFst"):
                  {m: (400 if i < 12 else 200) for i, m in enumerate(MONTHS_24)}},
        projects={lang: {m: 70_000_000 for m in MONTHS_24} for lang in ("cs", "pl")},
    )


def test_compare_pipeline_end_to_end(tmp_path):
    client = _fasting_client()
    resolved = resolve(client, ["pl", "cs"], topic="fasting")
    spec = pipeline.build_spec(client, resolved, "fasting", ["pl", "cs"], 24, date(2026, 9, 25))
    assert (spec["start"], spec["end"]) == ("2024-09", "2026-08")

    result = pipeline.analyze_spec(client, spec, tmp_path)
    assert result["languages"]["pl"]["status"] == "no_article"
    cs = result["languages"]["cs"]
    assert cs["status"] == "ok" and cs["views_growth_pct"] == -50.0 and cs["share_growth_pct"] == -50.0
    assert result["period"] == {"previous": "2024-09..2025-08", "recent": "2025-09..2026-08", "notes": []}
    for name in ("chart", "data", "result"):
        assert (tmp_path / result["files"][name].split("/")[-1]).exists()
    assert json.loads((tmp_path / "result.json").read_text())["ranking_by_share_growth"] == ["cs"]
    csv_lines = (tmp_path / "monthly.csv").read_text().splitlines()
    assert csv_lines[0] == "month,lang,article_views,project_views,share_per_million"
    assert len(csv_lines) == 1 + 2 * 24


def test_article_without_any_views_still_renders(tmp_path):
    client = _fasting_client()
    client.articles.clear()  # API answers 404 = no views in the range
    resolved = resolve(client, ["cs"], topic="fasting")
    spec = pipeline.build_spec(client, resolved, "fasting", ["cs"], 24, date(2026, 9, 25))
    result = pipeline.analyze_spec(client, spec, tmp_path)
    assert result["languages"]["cs"]["views_recent"] == 0
    assert "no recorded views in the whole period" in result["languages"]["cs"]["notes"]
    assert (tmp_path / "chart.png").exists()


def test_no_stale_chart_when_nothing_can_be_plotted(tmp_path):
    client = _fasting_client()
    resolved = resolve(client, ["cs"], topic="fasting")
    spec = pipeline.build_spec(client, resolved, "fasting", ["cs"], 24, date(2026, 9, 25))
    pipeline.analyze_spec(client, spec, tmp_path)
    assert (tmp_path / "chart.png").exists()

    # Same folder, now only a language without an article: the old chart must go.
    resolved = resolve(client, ["pl"], topic="fasting")
    spec = pipeline.build_spec(client, resolved, "fasting", ["pl"], 24, date(2026, 9, 25))
    result = pipeline.analyze_spec(client, spec, tmp_path)
    assert not (tmp_path / "chart.png").exists()
    assert "chart" not in result["files"]
    assert any("no chart" in n for n in result["period"]["notes"])


def test_missing_languages_are_listed_on_the_chart(tmp_path, monkeypatch):
    captured = {}
    real_render = pipeline.chart.render

    def spy(*args, **kwargs):
        captured.update(kwargs)
        return real_render(*args, **kwargs)

    monkeypatch.setattr(pipeline.chart, "render", spy)
    client = _fasting_client()
    resolved = resolve(client, ["pl", "cs"], topic="fasting")
    spec = pipeline.build_spec(client, resolved, "fasting", ["pl", "cs"], 24, date(2026, 9, 25))
    pipeline.analyze_spec(client, spec, tmp_path)
    assert captured["order"] == ["pl", "cs"]
    assert captured["not_shown"] == {"pl": "no article on this topic"}


def test_colors_follow_requested_order():
    from wikitrends.chart import SERIES_COLORS, assign_colors
    assert assign_colors(["pl", "cs"])["cs"] == SERIES_COLORS[1]  # same color whether pl has data or not
    assert assign_colors(["cs"])["cs"] == SERIES_COLORS[0]


def test_unpublished_last_month_shifts_period():
    client = _fasting_client()
    for series in client.projects.values():
        series.pop("2026-08")
    resolved = resolve(client, ["cs"], topic="fasting")
    spec = pipeline.build_spec(client, resolved, "fasting", ["cs"], 24, date(2026, 9, 2))
    assert spec["end"] == "2026-07"
    assert "not published yet" in spec["notes"][0]


def test_period_before_data_start_is_rejected():
    client = _fasting_client()
    resolved = resolve(client, ["cs"], topic="fasting")
    with pytest.raises(pipeline.SpecError, match="starts at 2015-07"):
        pipeline.build_spec(client, resolved, "fasting", ["cs"], 240, date(2026, 9, 25))


# --- API client -------------------------------------------------------------

class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.ok, self.url, self.text = status < 400, "u", json.dumps(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses, self.headers, self.calls = list(responses), {}, 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_client_sends_user_agent_retries_and_caches(tmp_path):
    session = FakeSession([FakeResponse(429, headers={"Retry-After": "1"}),
                           requests.ConnectionError("boom"),
                           FakeResponse(200, {"ok": 1})])
    sleeps = []
    client = Client(cache_dir=tmp_path, session=session, sleep=sleeps.append)
    assert "github.com/rublen/wikipedia-interest-trends" in session.headers["User-Agent"]
    assert session.headers["User-Agent"] == user_agent()
    assert client.get_json("https://x/y") == {"ok": 1}
    assert session.calls == 3 and sleeps == [1, 2]
    assert client.get_json("https://x/y") == {"ok": 1}  # served from cache
    assert session.calls == 3


def test_client_404_and_persistent_errors(tmp_path):
    client = Client(cache_dir=tmp_path, session=FakeSession([FakeResponse(404)]), sleep=lambda s: None)
    with pytest.raises(NotFound):
        client.get_json("https://x/404")
    client = Client(cache_dir=tmp_path, session=FakeSession([FakeResponse(503)] * 4), sleep=lambda s: None)
    with pytest.raises(ApiError, match="after 4 attempts"):
        client.get_json("https://x/503")
