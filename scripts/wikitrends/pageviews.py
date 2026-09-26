"""Monthly pageviews (agent=user) per article and per project (whole language edition)."""

from __future__ import annotations

from urllib.parse import quote

from wikitrends.api import Client, NotFound
from wikitrends.months import add_months, api_end, api_start, from_api_timestamp, month_range

PAGEVIEWS_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
RECENT_TTL = 24 * 3600  # the latest month may still be missing/incomplete; refresh daily


def _ttl(end: str, last_complete: str) -> float | None:
    """Months older than the last complete one are final and can be cached forever."""
    return None if end < add_months(last_complete, -1) else RECENT_TTL


def _series(items: list[dict], start: str, end: str) -> dict[str, int]:
    """API items -> {month: views} over the full range; months the API omits count as 0."""
    views = {from_api_timestamp(item["timestamp"]): item["views"] for item in items}
    return {month: views.get(month, 0) for month in month_range(start, end)}


def article_monthly(client: Client, lang: str, title: str, start: str, end: str, last_complete: str) -> dict[str, int]:
    article = quote(title.replace(" ", "_"), safe="")
    url = (f"{PAGEVIEWS_API}/per-article/{lang}.wikipedia/all-access/user/{article}"
           f"/monthly/{api_start(start)}/{api_end(end)}")
    try:
        items = client.get_json(url, ttl=_ttl(end, last_complete))["items"]
    except NotFound:
        items = []  # the API answers 404 when there are no views in the range
    return _series(items, start, end)


def project_monthly(client: Client, lang: str, start: str, end: str, last_complete: str) -> dict[str, int]:
    url = (f"{PAGEVIEWS_API}/aggregate/{lang}.wikipedia/all-access/user"
           f"/monthly/{api_start(start)}/{api_end(end)}")
    try:
        items = client.get_json(url, ttl=_ttl(end, last_complete))["items"]
    except NotFound:
        items = []
    return _series(items, start, end)
