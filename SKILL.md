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
| `ok` | Read `key_findings[0]` ("Analyzing: …"). If that is not what the user means, rerun **once** with a fitting `--qid` from `topic.resolution.candidates`. If none fits, stop and ask the user, as for `ambiguous`. Otherwise answer (below). |
| `ambiguous` | `resolution.reason` says why and what to do. If the user's context clearly points to one candidate in `resolution.candidates` (e.g. "chemistry app" → the element), or the reason suggests a concept to search, say which you chose and rerun **once**. Otherwise **stop**: list 2–3 candidates (label + description), ask which one, and end your reply. Never run the analysis on a guess. |
| `not_found` | At most **2 retries**: first the English name, then a different wording (or `--search-lang`). Still not found: tell the user and ask for another term. |
| `error` | Report the message. Network errors: retry once. |

Per language, `languages.<code>.status`: `ok` = analyzed; `no_article` = that Wikipedia has
no article on the topic (a finding: report it, don't hide it); `unknown_language` = wrong code.

## Writing the answer

The script has already done every calculation and comparison. Your job is to put its
sentences in order and quote them. **Never compare languages yourself** (which is largest,
fastest, the only one, which group a language belongs to): every such statement must be a
quote from `key_findings` or `comparison`. Never state a number that isn't in the output.

In this order:

1. **What was measured**: quote `key_findings[0]` ("Analyzing: …", including the proxy
   note if there is one) and `period.comparison` with the `period.recent` and
   `period.previous` months.
2. **Key findings**: quote the rest of `key_findings`, verbatim, always.
3. **Comparison** (2+ languages): quote `comparison`.
4. **Per language**: quote each language's `line` (many languages) or `summary` (one or two
   languages). They already contain the verdict, the confidence and what that confidence
   means; don't describe the level in your own words. For all reasons behind one result,
   quote its `trend.reasons` (in `files.result` or with `--details` for many languages).
5. **Which to explore next** (when asked): quote the `recommendation` lines verbatim,
   including the "Ranking weights" line. Don't add business reasons of your own (market,
   investment, "safer bet", demand, competition, saturation): the data doesn't show them.
   Recommendations are about **what to check next**, never a go/no-go on the product.
6. **Scope**: quote the `scope` sentence once, verbatim.
7. **Files**: give `files.chart`, and `files.report` if a report was made.

Changes are in words; a "no clear change" has no direction on purpose, so never call it
growth or decline. Seasonality is already handled (same months a year earlier); don't cite
it as a weakness. Detected bots are already excluded from the numbers.

## Follow-up questions

Rerun `compare` with the changed languages, period, topic or weights (add `--report`
again if the user wants an updated report). Downloads are cached, so reruns are fast.
For the same topic, reuse the `--qid` from the previous result.

Debugging only: `resolve` (writes `query.json`), `fetch --spec`, `analyze --spec`.
