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

### 1. MVP: answer example #1 end-to-end — ✅ done (Haiku runs passed; manual checks in `evals/verification-log.md`)
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

### 2. Trustworthy analysis: example #2 — built; calibrated on real topics
Goal: for each language, decide whether a change is real and lasting, or noise, a
one-off event, or a data artifact. The script runs transparent checks; the agent quotes
the result.

**Comparison (all checks):** the last N complete months vs **the same calendar months a
year earlier** (year-on-year), so seasonality cancels out, for any `--months N`. Above 12,
the comparison is 12 vs 12 and extra months only extend the chart and the history the
checks use. Headline share = sum of article views ÷ sum of project views per period.

| # | Check | Rule (as implemented in `scripts/wikitrends/trust.py`) | Cap |
|---|---|---|---|
| — | Verdict | `no_clear_change` if the change in share is < 10%, or smaller than the noise band **and** the sign test isn't significant; else growing / declining | — |
| 5 | Noise | Spread of the paired year-on-year log-changes → "±X% chance alone could produce" (2 standard errors) | verdict |
| — | Sign test | ≥ 10 of 12 changed months in one direction (one-sided p < 0.025; ties left out) also counts as a clear change | verdict |
| 1 | Volume | Smaller of the two periods' average monthly views: < 1,000 → medium, < 100 → low | medium / low |
| 2 | Spikes | Verdict from medians (typical months) differs from the verdict from totals → spike-driven. Spike = month > 3× the median month | low |
| 3 | Consistency | Months in the verdict's direction vs a year earlier: ≥ 80% ok, ≥ 65% medium, else low | medium / low |
| 4 | Raw vs share | Raw-views verdict differs from the share verdict → conclusion relies on normalization | medium |
| 6a | New/renamed article | No views before a compared month | low |
| 6b | Vanished article | ≥ 2 trailing zero months after normal traffic | low |
| 6c | Level shift | Year-on-year ratio jumps ≥ 3× (3-month medians) → abrupt shift; the year is chosen by medians, the month by the largest step. Shifts in the last 3 months are "too recent to tell" | low |
| 6d | Bots | Detected `automated` > 50% of views in a period (popular articles often have 20–45%) | medium |
| 6e | Old data | Comparison starts before May 2020 (bot flagging) | medium |
| — | Short comparison | Fewer than 6 months compared | medium |

- **Confidence** = the lowest cap; the reasons that lowered it come first. The script adds
  "Verdict: …, with … confidence: <reasons>" to each language's `summary`.
- Calibration (2026-09-26, 9 topics × 2–4 languages): the first version called clear
  declines "no clear change" (noise measured within periods included seasonality and the
  trend), capped half of all results on bot share (20% was too strict), and missed or
  mislocated abrupt shifts (Polish "ChatGPT", April 2026). Each finding changed a rule and
  added a regression test in `tests/test_trust.py`.
- Every result states the limit of the method: Wikipedia interest ≠ willingness to pay
  or market size; it's a signal for choosing what to validate next.

### 3. Report: example #3 — built; ranking and report fixed after the first Haiku batch
- **Two output channels, on purpose.** Agent-facing output (stdout, `result.json`) states every
  change in words and never shows a signed number; a "no clear change" gets its size relative to
  the noise ("moved 1.6%, within the ±14% normal fluctuation") and no direction. Human-facing
  output (the CSV and the PDF table) keeps the signed numbers. Reason: in Haiku runs, signs were
  misread ("shrank 8.8%" reported as "grew") and noise-level directions over-read ("rose 1.6%"
  reported as "growing"), while people read signed tables without trouble.
- `compare … --report [--question] [--note]` → one-page A4 PDF (question, what was measured,
  chart, ranked table, recommendation, trust reasons, method and limits); matplotlib only,
  font fallback with a glyph check for non-Latin titles.
- Transparent, user-adjustable ranking (`--weights`): momentum (only confirmed changes count),
  size (log views) and confidence; a code-written `why` per language and `recommendation`.

### Tuning on cheap models: stopping criterion and what it taught

**Stopping criterion (set 2026-09-27, before the next batch):** stop tuning the answer format
when **all critical rubric items pass in ≥ 4 of 5 runs of example #3**, with no critical
failure in the example #1 and #2 regression runs. Then move on to a **holdout set** of new
scenarios the format was never tuned on, and to the roadmap. Reason: several batches were
tuned against the same three prompts, which risks overfitting to them, the same risk as
calibrating thresholds on a few topics.

**Findings (design principles for agent-facing output), each backed by scored runs in
`evals/cheap-model-runs.md`:**
1. **Short, atomic sentences get quoted; long text gets paraphrased, and errors enter in the
   paraphrase.** Every code-written sentence that was quoted stayed correct; failures appeared
   in the model's own wording around the quotes, and more often when the text to quote grew.
2. **Never hand the model data it has to compare or rank itself.** A line listing views per
   month without the size rank led two runs to call the second-smallest audience "the smallest".
   Give ranks, directions and comparisons already computed.
3. **Signs get misread and noise-level directions get over-read.** "-8.8" became "grew 8.8%";
   "rose 1.6%" (inside the noise) became "growing". Hence words instead of signs, and no
   direction for a "no clear change" (see the two output channels above).
4. **Anything left undefined gets an invented meaning.** "Medium confidence" became "weak
   signal" and "real enough to act on" until the script wrote the meaning next to the level.
5. **Name the metric in every sentence.** "10 of 12 months were below" became "months with
   fewer views" (the count is on the share) in three runs, until the reason said "the share".

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
