# Plan: Wikipedia Interest Trends skill

An Agent Skill that lets an AI agent (including cheap models such as Claude Haiku 4.5)
analyze Wikipedia pageviews across language editions, produce charts and one-page PDF
reports, and give data-backed, caveated recommendations to B2C founders.

## Principles

- **Code does the thinking about data.** The agent calls CLI commands and reads compact
  JSON; it never writes analysis code. Trend verdicts and confidence are computed by the
  scripts, not improvised by the model.
- **Built for a small model.** One primary command (facade) per request type, explicit
  flags, short outputs, one uniform invocation. `SKILL.md` stays short; details live in
  `references/`.
- **Every claim carries its evidence.** Raw and normalized numbers, confidence, and
  limitations appear in each result and report.
- **The repo root is the skill directory.** Everything shipped lives here; no compiled
  binaries; environment reproducible from the lockfile.
- **English** for the skill, code, docs, and reports (first iterations).

## Data sources (free, no API key)

| Source | Use |
|---|---|
| Pageviews API `per-article/{lang}.wikipedia/all-access/user/{title}/monthly/...` | Monthly `agent=user` views per article (data from July 2015); see note below |
| Pageviews API `aggregate/{lang}.wikipedia/all-access/user/monthly/...` | Project totals, for normalization |
| Wikidata (`wbsearchentities`, `wbgetentities` sitelinks) | Topic → QID → article title in each language |

**Agent types.** `all-agents` = `user` + `spider` (self-declared crawlers) + `automated`
(heuristically detected bots, classified **only since April 2020**). `user` is
"not identified as a bot", not "verified human": before April 2020 it still contains
disguised bots, so windows crossing that date need a caveat, and spikes may be
undetected bots. Report the bot share as a quality signal.

All requests go through one API client that sends a descriptive `User-Agent` with
contact info (required by Wikimedia) from day one. Without it the API returns
**403** (checked 2026-09-25: empty and `python-requests/…` user agents are both refused).
- Format: `wikipedia-interest-trends/<version> (https://github.com/rublen/wikipedia-interest-trends) python-requests/<version>`;
  the public repo URL is the contact, and no email is embedded.
- `WIT_CONTACT` env var lets heavy users put their own contact in the header.
- Be polite: cache responses, request sequentially, back off on `429`.

## Repository layout (repo root = skill)

```
wikipedia-interest-trends/
├── SKILL.md
├── README.md                # human-facing; states "requires uv, or Python 3.11+"
├── PLAN.md
├── setup.sh
├── pyproject.toml           # [tool.uv] package = false
├── uv.lock
├── requirements.txt         # exported from uv.lock (fallback path)
├── scripts/
│   ├── wit.py               # CLI entry point
│   └── wikitrends/          # shared code (api client, resolve, fetch, analyze, plot, …)
├── references/              # interpretation guide, response template, …
├── tests/                   # offline tests on fixture data
└── evals/                   # scenario prompts, recorded runs, verification log
```

## Environment & setup

- uv project: `pyproject.toml` + `uv.lock`, `requires-python = ">=3.11"`.
- **Not a package:** `[tool.uv] package = false`. Running `scripts/wit.py` puts `scripts/`
  on `sys.path`, so `import wikitrends` works on both setup paths without installing
  anything.
- Fallback file: `uv export --format requirements-txt --no-dev --no-emit-project -o requirements.txt`
  (no `-e .` line; no dev tools like pytest). A check verifies it matches the lockfile.
- `setup.sh` (idempotent, never installs anything silently):
  1. `uv` found → `uv sync --locked` (**main path**).
  2. No uv, but `python3` ≥ 3.11 → `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
     (**fallback**, still pinned).
  3. Neither → exit with a distinct code and print the official uv install command. The
     agent shows it to the user and **asks permission** before running it.
- Both paths produce `.venv/`, so the agent always runs
  `.venv/bin/python scripts/wit.py <command> …`. Developers can use
  `uv run --locked scripts/wit.py …`.

## Iterations

### 0. Skeleton — ✅ done
- Clean `.gitignore`; add `pyproject.toml`, `uv.lock`, exported `requirements.txt`,
  `setup.sh`, stub `scripts/wit.py` + `scripts/wikitrends/`, minimal `SKILL.md`.
- ✅ `./setup.sh && .venv/bin/python scripts/wit.py --help` works on both setup paths.

### 1. MVP: answer example #1 end-to-end — built; Haiku run passed; manual check pending
- **Primary path, a facade:** `wit.py compare "<topic>" --langs pl,cs --months 24`
  chains resolve → fetch → analyze → chart in one call. Fewer calls means fewer failures
  on a cheap model.
- Subcommands kept for debugging: `resolve`, `fetch`, `analyze`. Handoff between them is
  a query spec: `resolve` writes `query.json` (QID, titles per language, period) and
  prints its path; later commands take `--spec path`.
- **Ambiguity:** if the Wikidata search is ambiguous, return the top 3 candidates with
  descriptions (no silent first pick); the agent chooses or asks the user, then reruns
  with `--qid Q…`.
- **Normalization:** fetch project totals too; report the article's share of project
  views (per million) alongside raw growth, because pl and cs totals move independently.
- **Windows:** exclude the current incomplete month; compare the last N/2 complete months
  with the previous N/2.
- Output: compact JSON (per language: raw views, raw growth %, share growth %, missing
  editions) + PNG chart.
- ✅ Acceptance:
  - "Compare intermittent fasting interest in pl vs cs Wikipedia over the last two years"
    is answered using only the skill. Note: Wikidata Q1666254 has **no plwiki article**
    (checked 2026-09-25), so a correct answer reports pl as missing instead of failing.
  - The full scenario runs on a **cheap model** (Claude Haiku 4.5 and/or an OpenRouter
    model); friction found there feeds back into `SKILL.md` and CLI output.
  - At least one number is **checked by hand against pageviews.wmcloud.org**; this is
    the first entry in `evals/verification-log.md`.

### 2. Trustworthy analysis: example #2
Goal: for each language, decide whether a change is real and lasting, or noise, a
one-off event, or a data artifact. The script runs transparent checks; the agent only
relays the result.

| # | Check | Question | Rule (initial thresholds, to be tuned and documented) |
|---|---|---|---|
| 1 | Volume | Enough data to trust? | < ~1,000 views/month → at most medium; < ~100 → low |
| 2 | Spike vs broad growth | One event or a real shift? | Recompute growth without the largest month (and via medians); if the growth disappears → spike-driven |
| 3 | Month-by-month consistency | Steady or random? | Count months above the same month a year earlier (e.g. 11/12 = steady, ~6/12 = noise); same-month comparison also handles seasonality |
| 4 | Raw vs normalized agreement | Topic or whole-wiki effect? | Raw and share growth in the same direction → stronger; opposite → explain, rely on share |
| 5 | Change vs normal noise | Big enough to matter? | Changes within the topic's usual year-to-year variation → verdict "flat / no clear change" |
| 6 | Data artifacts | Is the series itself sound? | Article created inside the window (fake growth); renames/redirects (fake collapse); high `automated`/`spider` share; window crossing April 2020 (bot classification change) |

- Missing language editions are reported as findings ("no article in pl"), not errors.
- **Verdict:** growing / flat / declining. **Confidence:** high / medium / low, equal to
  the **weakest** important check, always with plain-language reasons, e.g.
  `{"verdict": "growing", "share_growth_pct": 18.4, "confidence": "medium", "reasons": ["10 of 12 months above the same month last year", "growth holds without the largest month", "low volume: ~600 views/month"]}`.
- Rules of thumb over black-box statistics for now: founders can challenge every reason,
  a small model only relays them, reviewers can verify them against the raw data.
- Every result states the limit of the method: Wikipedia interest ≠ willingness to pay
  or market size; it's a signal for choosing what to validate next.
- Offline unit tests for every check on fixture series (steady growth, single spike,
  seasonal, new article, low volume).

### 3. Report: example #3
- `wit.py report` → one-page PDF (chart, key numbers, ranking, recommendation,
  assumptions, limitations); matplotlib-only to keep dependencies small.
- Transparent, user-adjustable ranking score (users bring their own criteria).

### 4. Follow-ups & efficiency
- On-disk cache + reuse of the query spec, so "add Slovak" or "same for 5 years" are
  cheap.
- Batch mode (many topics × languages per call).
- `references/`: interpretation guide and response template for the agent.

### 5. Evaluation on cheap models
- Scenario evals (~6–10): the three examples, follow-ups, edge cases (topic missing in a
  language, ambiguous topic, typos).
- Run each with Claude Haiku 4.5 and an OpenRouter model; record transcripts; keep
  extending the verification log.

### 6. Roadmap write-up (how to grow the skill)
- Multi-article topics (article baskets, categories, Wikidata-based expansion).
- Bulk pageview dumps instead of the API; DuckDB/Parquet storage for large volumes.
- Corroboration as a confidence check (#7): does the same direction appear in other
  languages and in related articles (e.g. Astronomy, Telescope, Solar eclipse)?
- Stronger statistics (trend tests, confidence intervals, seasonality decomposition,
  forecasting) replacing the rules of thumb inside checks 3 and 5, same output format.
- Additional signals (edits, Google Trends) and a regression eval suite.
