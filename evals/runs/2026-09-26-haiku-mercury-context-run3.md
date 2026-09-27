# Run: 2026-09-26-haiku-mercury-context-run3

**Prompt:** We're building a chemistry learning app. Is interest in mercury growing in the Ukrainian and Polish Wikipedia over the last two years?

**Model:** `claude-haiku-4-5-20251001`

**Tool call — Skill:**

```json
{
 "skill": "wikipedia-interest-trends",
 "args": "topic: mercury, languages: uk,pl, timeframe: 2 years"
}
```

<details><summary>Tool result</summary>

```
Launching skill: wikipedia-interest-trends
```
</details>

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/setup.sh",
 "description": "Set up the Wikipedia interest trends skill"
}
```

<details><summary>Tool result</summary>

```
setup: using uv (uv 0.12.18 (Homebrew 2026-09-22 aarch64-apple-darwin))
setup: OK - run with: .venv/bin/python scripts/wit.py --help
```
</details>

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py compare \"mercury\" --langs uk,pl --months 24",
 "description": "Analyze mercury interest in Ukrainian and Polish Wikipedia over the last 2 years"
}
```

<details><summary>Tool result</summary>

```
{
 "status": "ambiguous",
 "message": "'mercury' matches several Wikidata items. Pick the one the user means (ask if unclear) and rerun with --qid.",
 "resolution": {
  "method": "search",
  "decision": "ambiguous",
  "reason": "search result #1 (Q613883 Mercury, 27 Wikipedias) is not the most-linked item (Q308 Mercury, 250)",
  "rule": "auto-pick only if search result #1 is also the item with the most Wikipedia articles, with at least 2x the runner-up",
  "best": {
   "qid": "Q308",
   "label": "Mercury",
   "wikipedias": 250
  },
  "runner_up": {
   "qid": "Q925",
   "label": "mercury",
   "wikipedias": 176
  },
  "ratio": 1.42,
  "candidates": [
   {
    "search_rank": 1,
    "qid": "Q613883",
    "label": "Mercury",
    "description": "automobile marque of the Ford Motor Company",
    "wikipedias": 27
   },
   {
    "search_rank": 2,
    "qid": "Q1231263",
    "label": "Mercury",
    "description": "commune in Savoie, France",
    "wikipedias": 35
   },
   {
    "search_rank": 3,
    "qid": "Q308",
    "label": "Mercury",
    "description": "first planet from the Solar System and smallest among all, tellurian and with extreme tem…",
    "wikipedias": 250
   },
   {
    "search_rank": 4,
    "qid": "Q165745",
    "label": "Mercury Records",
    "description": "American record label",
    "wikipedias": 40
   },
   {
    "search_rank": 5,
    "qid": "Q925",
    "label": "mercury",
    "description": "chemical element with symbol Hg and atomic number 80",
    "wikipedias": 17
… [324 more chars]
```
</details>

### Assistant

For a chemistry app, you mean the chemical element (mercury, Hg). Let me pull the data for that:

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py compare \"mercury\" --langs uk,pl --months 24 --qid Q925",
 "description": "Analyze mercury (chemical element) interest in Ukrainian and Polish Wikipedia"
}
```

<details><summary>Tool result</summary>

```
{
 "status": "ok",
 "topic": {
  "query": "mercury",
  "qid": "Q925",
  "label": "mercury",
  "description": "chemical element with symbol Hg and atomic number 80",
  "resolution": {
   "method": "qid",
   "decision": "given_qid",
   "reason": "chosen with --qid Q925"
  }
 },
 "period": {
  "previous": "2024-09..2025-08",
  "recent": "2025-09..2026-08",
  "notes": []
 },
 "languages": {
  "uk": {
   "status": "ok",
   "title": "Ртуть",
   "summary": "Article views fell 52.9% (20,960 -> 9,876). The whole uk Wikipedia shrank 24.6% over the same time, so the article's share of all views fell 37.5%: it lost ground relative to the rest of that Wikipedia.",
   "views_previous": 20960,
   "views_recent": 9876,
   "views_growth_pct": -52.9,
   "avg_monthly_views_recent": 823,
   "share_per_million_previous": 23.28,
   "share_per_million_recent": 14.56,
   "share_growth_pct": -37.5,
   "project_growth_pct": -24.6,
   "first_month_with_data": "2024-09",
   "notes": []
  },
  "pl": {
   "status": "ok",
   "title": "Rtęć",
   "summary": "Article views fell 27.7% (51,273 -> 37,077). The whole pl Wikipedia shrank 8.8% over the same time, so the article's share of all views fell 20.7%: it lost ground relative to the rest of that Wikipedia.",
   "views_previous": 51273,
   "views_recent": 37077,
   "views_growth_pct": -27.7,
   "avg_monthly_views_recent": 3090,
   "share_per_million_previous": 20.71,
   "share_per_million_recent": 16.43,
   "share_growth_pct": -20.7,
   "project_growth_pct":
… [1104 more chars]
```
</details>

### Assistant

**Interest in mercury is declining in both Ukrainian and Polish Wikipedia.**

**What was measured:** Mercury (chemical element Hg), comparing Sept 2024–Aug 2025 vs. Sept 2025–Aug 2026.

**Results:**

**Polish** ("Rtęć"): Article views fell 27.7% (51,273 → 37,077). The whole pl Wikipedia shrank 8.8% over the same time, so the article's share of all views fell 20.7%: it lost ground relative to the rest of that Wikipedia. (3,090 avg monthly views recently)

**Ukrainian** ("Ртуть"): Article views fell 52.9% (20,960 → 9,876). The whole uk Wikipedia shrank 24.6% over the same time, so the article's share of all views fell 37.5%: it lost ground relative to the rest of that Wikipedia. (823 avg monthly views recently)

**Comparison:** Ranked by change in share of attention, best first: pl (share fell 20.7%), uk (share fell 37.5%).

**Caveats:** These numbers are indicative—no confidence level is computed yet. Pageviews measure curiosity among Wikipedia readers, not willingness to market a course. The data excludes identified bots but may include undetected ones.

**Chart & data:** [`chart.png`](<repo>/output/Q925-mercury/chart.png) and [`monthly.csv`](<repo>/output/Q925-mercury/monthly.csv)

For a chemistry learning app, interest in mercury is moving *away* from both these markets over the past year.

---

Turns: 6 · Duration: 24 s · Cost: $0.0291

