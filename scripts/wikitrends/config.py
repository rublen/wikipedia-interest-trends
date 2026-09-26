"""Paths and identity shared by all modules."""

from __future__ import annotations

import os
from pathlib import Path

import requests

from wikitrends import __version__

SKILL_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.environ.get("WIT_CACHE_DIR", SKILL_ROOT / ".cache"))
OUTPUT_DIR = Path(os.environ.get("WIT_OUTPUT_DIR", SKILL_ROOT / "output"))

REPO_URL = "https://github.com/rublen/wikipedia-interest-trends"


def user_agent() -> str:
    """Wikimedia requires a descriptive User-Agent with contact info; generic ones get 403."""
    contact = os.environ.get("WIT_CONTACT", REPO_URL)
    return f"wikipedia-interest-trends/{__version__} ({contact}) python-requests/{requests.__version__}"
