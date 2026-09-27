# Roadmap

How to develop the skill further. Evidence comes from the scored agent runs in
[`evals/`](../evals/); iteration history and design findings are in [`PLAN.md`](../PLAN.md).

## 1. Current state

What works, and how it was measured:

| Area | Evidence |
|---|---|
| Data correctness | 81 offline tests (synthetic series with known answers for every trust check; every code-written sentence); 3 manual checks against pageviews.wmcloud.org and Wikidata ([verification log](../evals/verification-log.md)), one of which found and fixed a counting bug |
| Answers on a cheap model (Claude Haiku 4.5), final version | 22 runs, **11** with all critical rubric items passed: last tuning batch 3/7, one user-driven run 0/1, **holdout 8/14** ([holdout](../evals/holdout.md)) |
| What holds in those runs | facts written by code (numbers, units, verdicts, confidence) are quoted correctly in all but one run; missing or new language editions and follow-up questions: 4/4 holdout runs |
| Free models (OpenRouter) | 2 runs: one passed every item (`openrouter/free`, five models mixed in one run); one failed four critical items and fabricated a quote (`nvidia/nemotron-3.5-lightning:free`) |
| Grounding checker ([`evals/grounding.py`](../evals/grounding.py)) | tuned set, 10 transcripts: flagged exactly the two known fabrications, nothing else. Holdout, 14 runs: 2 false positives (Ukrainian decimal commas), no misses; no fabrications occurred, so sensitivity on new data is unmeasured |

Tuning stopped at a criterion set in advance (all critical items in ≥ 4 of 5 runs of the
report scenario); it reached 2 of 5. The remaining failures are listed below, not tuned further.

## 2. Known limitations

| Limitation | Count | Where |
|---|---|---|
| Models add their own interpretation when asked "why" ("safe bet", "market saturation") | 4 of 7 final tuning runs | run log |
| Guessing after an `ambiguous` answer without context | 1 of 2 | holdout H3 |
| A plural resolves to a different item ("apples" → the genus *Malus*) | 1 of 2 | holdout H2 |
| Non-English answers don't say the article is a proxy | 2 of 2 | holdout H4 |
| An invented direction on a "no clear change" ("+0,7%") | 1 of 2 | holdout H4 |
| Level-shift reason blames technical causes for the end of a news cycle | 2 of 2 | holdout H6 |
| Grounding checker misreads decimal commas | 2 of 14 runs | holdout |
| One article per language; related articles and redirects not counted | by design | — |
| Outputs are written inside the skill directory, not the user's project | by design | — |
| Pageviews ≠ willingness to pay; language audiences ≠ countries; undetected bots remain | by design | scope sentence |

## 3. Next iterations, in priority order

Each item is verified the same way: unit tests for the code change, then the affected holdout
scenarios rerun (≥ 2 runs each) and scored against the rubric, with the grounding check.

| # | Change | Problem it solves (evidence) | How we'd verify it |
|---|---|---|---|
| 1 | **Ready-to-quote answer.** The script writes the whole answer as Markdown (what was measured, findings, per language, recommendation, scope, files); the model translates if needed and adds only context | Own interpretation in 4 of 7 runs; in every batch, errors came from the model's own sentences, never from code-written ones | G8/G10 failures on the tuned examples and holdout drop to ≤ 1 in 14; follow-ups (H7) still work |
| 2 | **Make a guess after `ambiguous` visible, in code.** Code can't know whether the user chose, but when `compare "<topic>" --qid …` is called for a topic that is ambiguous, the first key finding says so: "chosen with --qid from several meanings of 'Java'; others: island (Q3757), coffee…" | A silent guess after `ambiguous`, 1 of 2 (H3); instructions in SKILL.md were not enough (finding 6) | H3 and the mercury scenario over ≥ 4 runs: every answer either asks, or names the choice and the other meanings |
| 3 | **Singular/plural fallback in `resolve`.** Search both forms; if they resolve to different items, return `ambiguous` with both | "apples" → *Malus* (H2) | Unit tests with plural/singular pairs; H2 over ≥ 4 runs |
| 4 | **Proxy statement in code-written text.** When `--note` marks a proxy, the per-language lines and key findings say so, so it survives translation | Proxy missing in 2 of 2 Ukrainian answers (H4) | H4 plus a second non-English scenario: proxy stated in every run |
| 5 | **Observation-only reason texts.** Reasons state what the data shows ("views fell from 179,071 to 2,310 in June 2025 and stayed low; April–May 2025 were spike months"), never speculative causes | H6: the listed causes (search engine, bots, rename) sent 2 of 2 answers the wrong way | H6 and two more news-driven topics: no answer attributes the change to a technical cause |
| 6 | **`check-answer` inside the skill.** The grounding check runs on the agent's draft before sending; ungrounded quotes or numbers come back as errors to fix | Nemotron's fabricated, attributed quote; checks inside the model don't work (finding 6) | Replay the Nemotron transcript: the draft is rejected; no new false positives on the holdout |
| 7 | **Decimal commas in the checker.** Parse locale decimals ("14,6%") | 2 false positives of 14 (H4) | Unit tests; holdout rerun: 0 false positives on the Ukrainian runs |

Also worth doing, lower priority: write outputs to the user's working directory; a chart layout
for more than 8 languages (small multiples).

## 4. Scaling to more complex research and larger data

| Need | Current state | Next step |
|---|---|---|
| **Topic clusters** instead of single articles ("astronomy" = the main article + telescope, solar system, eclipses…) | one Wikidata item, one article per language | Build a cluster from Wikidata links (subclass/part-of, a curated list, or the article's category), sum views per language, and add the views of redirects to each article (MediaWiki `prop=redirects`). Report per-cluster and per-article numbers so one article can't dominate unseen |
| **Many languages** | compact output above 2 languages; chart capped at 8 lines | Small-multiple charts and a table-first PDF for 10–50 languages; ranking already scales; group by region or script if asked |
| **Longer periods** | year-on-year comparison; data from July 2015; bot flagging only from May 2020 | Multi-year trend view (share per year and a trend test across years), with pre-2020 years marked as less reliable |
| **Concurrent fetching** | sequential requests: 3 per language (article views, bot views, wiki total) plus 4 for topic resolution and the publication check, cached | A bounded worker pool with a rate limiter and the existing backoff on 429/5xx, following Wikimedia's API guidelines; the User-Agent with contact stays |
| **Shared cache** | a per-machine disk cache (`.cache/`); complete past months cached forever | A shared store (SQLite or DuckDB file, or object storage) keyed by article, month and agent, so a team or a batch job reuses data; recent months keep a short TTL |
| **Bulk data** | per-article API calls | For hundreds of topics × many languages, use Wikimedia's pageview dumps (monthly "pageview complete" files) loaded into DuckDB/Parquet, and keep the API for small, fresh queries |

## 5. Evaluation roadmap

- **A bigger holdout:** 20–30 scenarios covering the weak areas found so far (non-English
  prompts, news-driven topics, ambiguous and plural topics, many languages, follow-up chains),
  with expectations committed before the runs, as now.
- **More runs per scenario:** at least 5, reporting pass rates with their spread; 2 runs can
  only separate "fails here" from "one bad run" roughly.
- **Human scoring:** a second scorer on a sample, measuring agreement with the current scores,
  since the rubric's judgment items (G5, G8, G10) are scored by the developing agent today.
- **More automation:** the grounding check and the string-matching items are already
  mechanical; add replayed tool outputs (fixtures) so agent runs don't depend on live data, and
  run the suite on every change to `SKILL.md` or the output format.
- **More models:** Haiku as the baseline, a pinned free model with tool calling, and a stronger
  model as a ceiling, to separate skill problems from model problems.
