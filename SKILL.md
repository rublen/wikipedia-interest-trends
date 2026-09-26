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

- Exit code 0: ready.
- Exit code 3: neither uv nor Python 3.11+ is installed. Show the user the install
  command that `setup.sh` printed and **ask for permission** before running it.

## Main command

```bash
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/wit.py compare "<topic in English>" --langs <codes> [--months 24]
```

- `--langs`: Wikipedia language codes, comma-separated: `uk` (Ukrainian), `pl`, `cs`
  (Czech), `de`, `en`, `es`, `pt`, `ja`… Not country codes (`ua`, `cz` are wrong).
- `--months`: even number of complete months (default 24). The first half is the
  "previous" window and the second half the "recent" window. "Last two years" = 24.
- Topic in another language: add `--search-lang uk` (etc.), or translate it to English.
- Always use `SKILL_DIR/.venv/bin/python`, never a system `python`.

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
   language, the two windows from `period`.
2. **Results per language**, in `ranking_by_share_growth` order: the language's
   `summary` (verbatim), plus `avg_monthly_views_recent` for scale. Change in share is the main
   comparison (it removes differences in each Wikipedia's size and overall traffic).
   With 2+ languages, add the `comparison` sentence.
3. **Notes**: every item in `languages.<code>.notes` and `period.notes`, and any
   `no_article` languages.
4. **Caveats**: the result has no confidence level yet (`not_yet_checked`), so call
   the numbers indicative, and mention the key `limitations` (interest ≠ willingness to pay).
5. **Chart**: give the path in `files.chart`. Data is in `files.data` (CSV).

Keep it short. Don't claim a trend is reliable or statistically significant.

## Follow-up questions

Rerun `compare` with the changed languages, period or topic. Downloads are cached, so
reruns are fast. For the same topic, reuse the `--qid` from the previous result.

Debugging only: `resolve` (writes `query.json`), `fetch --spec`, `analyze --spec`.
