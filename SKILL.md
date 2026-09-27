---
name: wikipedia-interest-trends
description: Analyze how interest in a topic changes over time across Wikipedia language editions, using Wikimedia pageview data. Use when the user asks which topics, courses or markets/languages to pursue, wants to compare interest in a topic between languages or over time, or needs a chart backed by Wikipedia pageviews.
---

# Wikipedia Interest Trends

Measures interest in a topic by monthly Wikipedia pageviews, per language edition,
and normalizes it by the size of each Wikipedia. The scripts do all data work;
you run one command and explain its JSON. **Never write your own analysis code.**

`SKILL_DIR` below = the base directory of this skill (shown when the skill loads).
Use full paths as written; **don't `cd`** into the skill directory.

## Setup (once)

```bash
SKILL_DIR/setup.sh
```

- Exit code 0: ready. It prints the exact command prefix to use
  (`<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py`); copy it as printed.
- Exit code 3: neither uv nor Python 3.11+ is installed. Show the user the install
  command that `setup.sh` printed and **ask for permission** before running it.

## Main command

```bash
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/wit.py compare "<topic in English>" --langs <codes> [--months 24]
```

- `--langs`: Wikipedia language codes, comma-separated: `uk` (Ukrainian), `pl`, `cs`
  (Czech), `de`, `en`, `es`, `pt`, `ja`… Not country codes (`ua`, `cz` are wrong).
- `--months N` (default 24): compares the last N complete months with **the same months
  a year earlier** (year-on-year, so seasons cancel out). Above 12, the comparison is
  the last 12 months vs the 12 before, and extra months only lengthen the chart history.
  "Last two years" = 24; "this spring vs last spring" = 3 (e.g. run in June).
- Topic in another language: add `--search-lang uk` (etc.), or translate it to English.
- Always use `SKILL_DIR/.venv/bin/python`, never a system `python`.

**Broad intents** ("learning English", "interest in astronomy courses") rarely have an
article of their own. Use the most widely available article that stands for the interest
(e.g. `--qid Q1860`, the English language, rather than "English as a second language",
which exists in few languages) and say it is a proxy, both in the answer and in `--note`.

### Reports and rankings

When the user asks for a report, something to share, or "which audiences/languages to
explore next", add:

- `--report`: also writes a one-page PDF (`files.report`).
- `--question "<the user's question>"`: the report's title.
- `--note "<what the article stands for>"`, e.g. "Proxy: the article on the English
  language, read in each audience's own language."
- `--weights momentum=0.4,size=0.4,confidence=0.2` (the default): change only if the user
  states priorities, e.g. "bigger markets matter most" → `size=0.6,momentum=0.2,confidence=0.2`.
  Momentum = change in share (a "no clear change" counts as 0), size = average monthly
  views, confidence = the trust level. Scores rank only the compared languages.

## Read the `status` field first

| status | What to do |
|---|---|
| `ok` | Check `topic.description` matches what the user means. If not, rerun with a `--qid` from `topic.resolution.candidates` or a more specific topic. Then answer (below). |
| `ambiguous` | `resolution.reason` says why. If the user's context clearly points to one candidate in `resolution.candidates` (e.g. "chemistry app" → the element), say which one you chose and rerun with `--qid Q…`. Otherwise **stop**: list 2–3 candidates (label + description), ask which one, and end your reply. Do not run the analysis on a guess. |
| `not_found` | Retry with the English name, a more common wording, or `--search-lang`. |
| `error` | Report the message. Network errors: retry once. |

Per language, `languages.<code>.status`:
`ok` = analyzed; `no_article` = that Wikipedia has no article on the topic (a finding:
report it, don't hide it); `unknown_language` = wrong language code.

## Writing the answer

Use only numbers from the JSON. The script already interprets them: **quote each
language's `summary` and the top-level `comparison` verbatim**, word for word. Don't
paraphrase them or add your own explanation of why numbers differ (no "despite",
"because", "reflects"). Don't work out directions from the `_pct` fields yourself. Structure:

1. **What was measured**: the Wikidata item (label, description), the article title per
   language, and `period.comparison` with the `period.recent` and `period.previous` months.
2. **Results per language**, in `ranking_by_share_growth` order: the language's
   `summary` (verbatim; it ends with the verdict, the confidence and its reasons), plus
   `avg_monthly_views_recent` for scale. Change in share is the main comparison (it
   removes differences in each Wikipedia's size and overall traffic). With 2+ languages,
   add the `comparison` sentence.
3. **Notes**: every item in `languages.<code>.notes` and `period.notes`, and any
   `no_article` languages.
4. **Trust**: the `summary` already states the verdict, the confidence and what that
   confidence level means; quote it and don't describe the level in your own words.
   If the user asks how far to trust a result, list that language's `trend.reasons`
   (verbatim). Seasonality is already handled (same months a year earlier); don't cite
   it as a weakness.
5. **Which to explore next** (when asked): quote the `recommendation` lines verbatim.
   They come from `ranking` (score, components and `why` per language); say which
   `ranking.weights` were used.
6. **Scope**: quote the top-level `scope` sentence once, verbatim. Add other
   `limitations` only if they matter for this question.
7. **Files**: always give the path in `files.chart`, and `files.report` if one was made;
   the data is in `files.data` (CSV).

Keep it short. Never state a higher confidence than `trend.confidence`, and don't call a
`no_clear_change` result growth or decline. Recommendations are about **what to check
next** (e.g. "validate demand in pl before uk"), never a go/no-go on the product: reader
interest alone can't decide that.

## Follow-up questions

Rerun `compare` with the changed languages, period, topic or weights (add `--report`
again if the user wants an updated report). Downloads are cached, so reruns are fast.
For the same topic, reuse the `--qid` from the previous result.

Debugging only: `resolve` (writes `query.json`), `fetch --spec`, `analyze --spec`.
