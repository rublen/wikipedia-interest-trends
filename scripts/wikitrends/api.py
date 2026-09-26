"""The single HTTP client for all Wikimedia requests: User-Agent, disk cache, backoff."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

import requests

from wikitrends.config import CACHE_DIR, user_agent

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
TIMEOUT_SECONDS = 30


class ApiError(Exception):
    """A request failed after retries, or returned an unexpected status."""


class NotFound(ApiError):
    """HTTP 404: for pageviews this usually means no views recorded in the range."""


class Client:
    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.cache_dir = Path(cache_dir) / "http"
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent()
        self.sleep = sleep
        self.network_requests = 0

    def get_json(self, url: str, params: dict[str, Any] | None = None, ttl: float | None = None) -> Any:
        """GET JSON, served from the disk cache when fresh.

        ttl: seconds a cached response stays valid; None means forever
        (use only for data that can no longer change, e.g. complete past months).
        """
        path = self._cache_path(url, params)
        if path.exists() and (ttl is None or time.time() - path.stat().st_mtime < ttl):
            return json.loads(path.read_text())

        data = self._fetch(url, params)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(path)
        return data

    def _fetch(self, url: str, params: dict[str, Any] | None) -> Any:
        for attempt in range(MAX_ATTEMPTS):
            self.network_requests += 1
            try:
                response = self.session.get(url, params=params, timeout=TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                error = f"network error: {exc}"
            else:
                if response.status_code == 404:
                    raise NotFound(url)
                if response.status_code not in RETRY_STATUSES:
                    if not response.ok:
                        raise ApiError(f"HTTP {response.status_code} for {response.url}: {response.text[:200]}")
                    return response.json()
                error = f"HTTP {response.status_code}"
                retry_after = response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    self.sleep(min(int(retry_after), 60))
                    continue
            if attempt < MAX_ATTEMPTS - 1:
                self.sleep(2**attempt)
        raise ApiError(f"{error} for {url} after {MAX_ATTEMPTS} attempts")

    def _cache_path(self, url: str, params: dict[str, Any] | None) -> Path:
        key = url + "?" + json.dumps(params or {}, sort_keys=True)
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / digest[:2] / f"{digest}.json"
