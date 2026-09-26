"""Offline stand-ins for the Wikimedia APIs."""

from __future__ import annotations

from wikitrends.api import NotFound
from wikitrends.months import from_api_timestamp, month_range


NON_WIKIPEDIA = {"abstractwiki", "commonswiki"}


def pageview_items(series: dict[str, int]) -> dict:
    return {"items": [{"timestamp": m.replace("-", "") + "0100", "views": v} for m, v in series.items()]}


class FakeClient:
    """Answers get_json from canned data: wikidata search/entities and pageview series."""

    def __init__(self, search=None, entities=None, articles=None, projects=None):
        self.search = search or {}        # text -> [{"id", "label", "description"}]
        self.entities = entities or {}    # qid -> {"labels", "descriptions", "sitelinks"} (API shape)
        self.articles = articles or {}    # (lang, title_in_url) -> {month: views}
        self.projects = projects or {}    # lang -> {month: views}
        self.network_requests = 0
        self.calls: list[str] = []

    def get_json(self, url, params=None, ttl=None):
        self.calls.append(url)
        if "meta.wikimedia.org" in url:  # site matrix: every fake sitelink is a Wikipedia...
            dbnames = {s for e in self.entities.values() for s in e.get("sitelinks", {})}
            dbnames -= NON_WIKIPEDIA  # ...except sister projects
            return {"sitematrix": {"count": 1, "0": {"code": "xx", "site": [
                {"dbname": d, "code": "wiki"} for d in sorted(dbnames)]}}}
        if "wikidata" in url:
            if params["action"] == "wbsearchentities":
                return {"search": self.search.get(params["search"], [])}
            return {"entities": {q: self.entities.get(q, {"missing": ""}) for q in params["ids"].split("|")}}
        parts = url.split("/")
        start, end = from_api_timestamp(parts[-2]), from_api_timestamp(parts[-1])
        if "/per-article/" in url:
            lang, title = parts[parts.index("per-article") + 1].split(".")[0], parts[-4]
            series = self.articles.get((lang, title))
        else:
            lang = parts[parts.index("aggregate") + 1].split(".")[0]
            series = self.projects.get(lang)
        if series is None:
            raise NotFound(url)
        in_range = {m: v for m, v in series.items() if m in month_range(start, end)}
        if not in_range:
            raise NotFound(url)
        return pageview_items(in_range)


def entity(label: str, description: str, sites: dict[str, str]) -> dict:
    return {
        "labels": {"en": {"value": label}},
        "descriptions": {"en": {"value": description}},
        "sitelinks": {site: {"title": title} for site, title in sites.items()},
    }


def many_sites(n: int, extra: dict[str, str] | None = None) -> dict[str, str]:
    """n fake Wikipedia sitelinks (plus explicit ones)."""
    # Real site ids are letters only (e.g. "plwiki"), so the fakes must be too.
    sites = {f"x{chr(97 + i // 26)}{chr(97 + i % 26)}wiki": f"T{i}" for i in range(n)}
    sites.update(extra or {})
    return sites
