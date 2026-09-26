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
| `ambiguous` | `resolution.reason` says why. Pick the candidate from `resolution.candidates` that fits the user's context and rerun with `--qid Q…`. If unclear, show the user 2–3 candidates (label + description) and ask. |
| `not_found` | Retry with the English name, a more common wording, or `--search-lang`. |
| `error` | Report the message. Network errors: retry once. |

Per language, `languages.<code>.status`:
`ok` = analyzed; `no_article` = that Wikipedia has no article on the topic (a finding:
report it, don't hide it); `unknown_language` = wrong language code.

## Writing the answer

Use only numbers from the JSON. Structure:

1. **What was measured**: the Wikidata item (label, description), the article title per
   language, the two windows from `period`.
2. **Results per language**: `share_growth_pct` is the main comparison number (views
   as a share of all views in that Wikipedia, so languages of different size and
   traffic trends are comparable). Also give `views_growth_pct`, `avg_monthly_views_recent`,
   and `project_growth_pct` when it explains a difference between raw and share growth.
   Order languages by `ranking_by_share_growth`.
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
