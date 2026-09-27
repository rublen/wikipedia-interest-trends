# wikipedia-interest-trends

An [Agent Skill](https://agentskills.io) that helps B2C founders decide which topics to develop
and which language audiences to explore next, using Wikipedia pageviews as a signal of reader
interest. An AI agent asks the questions in plain language; the skill's own Python code fetches
the data, compares, checks how far each result can be trusted, and writes the sentences the agent
quotes, plus a chart and a one-page PDF report.

The repository root is the skill directory; the agent's entry point is [`SKILL.md`](SKILL.md).
How to develop it further: [`docs/ROADMAP.md`](docs/ROADMAP.md).

> Pageviews measure reader interest on Wikipedia, not willingness to pay or market size:
> use this to choose what to validate next, not to decide on its own.

## What it does

- **Topic → the same article in every language.** Resolves a topic to a Wikidata item and its
  article in each requested Wikipedia. Ambiguous names ("mercury", "Java") come back as
  candidates to choose from; activity phrases ("learning English", "astronomy courses") are
  never auto-picked, because they tend to match niche items (e.g. a radio programme).
- **Year-on-year comparison.** The last N complete months vs the same months a year earlier, so
  seasonality cancels out. `--months` above 12 only lengthens the chart and history.
- **Normalized for Wikipedia's own traffic.** The main measure is the article's *share* of all
  views in its Wikipedia, so languages of different size, and wikis that are shrinking overall,
  are comparable.
- **Verdict, confidence and reasons.** growing / declining / no clear change, with high / medium /
  low confidence from transparent checks: volume, spikes (medians), month-by-month consistency,
  noise (paired changes and a sign test), raw vs normalized, new or vanished articles, abrupt
  level shifts, bot share, and data before May 2020.
- **Which audiences to explore next.** A transparent, adjustable ranking (momentum, size,
  confidence; `--weights`), with a code-written reason per language and recommendations framed as
  what to validate next.
- **Shareable output.** `chart.png`, a one-page A4 `report.pdf`, `monthly.csv` and `result.json`.

## Quick start

Requirements: **uv, or Python 3.11+**, a POSIX shell (macOS or Linux), and network access to
`wikimedia.org` and `wikidata.org`. Windows is not supported yet.

1. Install the skill for Claude Code (or any agent that reads Agent Skills):
   ```bash
   git clone https://github.com/rublen/wikipedia-interest-trends ~/.claude/skills/wikipedia-interest-trends
   ```
2. Ask your agent, for example:
   - *Compare the growth of interest in intermittent fasting in the Polish and Czech Wikipedia over the last two years.*
   - *We're thinking about adding an astronomy course to our app. Is interest growing on Ukrainian Wikipedia, and how far can we trust it?*
   - *We're building a language-learning app. Compare interest in learning English in Ukrainian, Polish, German, Spanish, Portuguese, Turkish, Japanese and Vietnamese, and prepare a short report: which audiences should we explore next, and why?*

   The agent runs `setup.sh` once, which creates a local environment with pinned packages; if
   neither uv nor Python 3.11+ is present, it installs nothing and the agent asks you before
   installing uv. Then it runs the skill's commands. Follow-ups such as "add German" or "weight audience size more" rerun from the cache.

### Setup, if you run it yourself

```bash
./setup.sh
```

| Situation | What `setup.sh` does |
|---|---|
| `uv` found | `uv sync --locked --no-dev` (main path) |
| no uv, Python ≥ 3.11 found | `python3 -m venv .venv` + `pip install -r requirements.txt` (pinned, hashed) |
| neither | exits with code 3 and prints the uv install command; installs nothing |

It prints the exact command to use. `WIT_SETUP=pip ./setup.sh` forces the fallback path.

### Command line

```bash
.venv/bin/python scripts/wit.py compare "intermittent fasting" --langs pl,cs
.venv/bin/python scripts/wit.py compare mercury --langs uk,en               # -> "ambiguous" + candidates
.venv/bin/python scripts/wit.py compare --qid Q1860 --langs uk,pl,de,ja \
    --report --question "Which audiences should we explore next?" \
    --note "Proxy: the article on the English language" --weights size=0.6,momentum=0.2,confidence=0.2
```

| Option | Meaning |
|---|---|
| `--langs` | Wikipedia language codes (`uk`, `pl`, `cs`, …), not country codes |
| `--months N` | last N complete months vs the same months a year earlier (default 24: 12 vs 12) |
| `--qid` | a Wikidata item, e.g. after an `ambiguous` answer |
| `--search-lang` | language the topic is written in (default `en`) |
| `--report`, `--question`, `--note` | one-page PDF, its title, and a note such as "Proxy: …" |
| `--weights` | ranking weights for momentum, size and confidence |
| `--details` | full per-language summaries even for many languages |

It prints one JSON object for the agent and writes files to `output/<QID>-<label>/`. API
responses are cached in `.cache/`. Agent-facing output states every change in words (no signed
numbers, no direction for a "no clear change"); the CSV and the PDF table keep the signed numbers
for people.

## Tested models and results

Each agent run was scored against a fixed rubric ([`evals/rubric.md`](evals/rubric.md)): 11
general items and 5 scenario items, split into *critical* (the answer would mislead or fail the
task) and *minor* (quoting, completeness). Transcripts are in [`evals/runs/`](evals/runs/).

| Model | Runs (final version) | All critical items passed |
|---|---|---|
| **Claude Haiku 4.5**, via Claude Code | 22 | **11** |
| · last tuning batch (the task's three examples) | 7 | 3 |
| · a user-driven run with the user's own wording | 1 | 0 |
| · **holdout**: 7 new scenarios × 2, never used for tuning ([`evals/holdout.md`](evals/holdout.md)) | 14 | **8** |
| Free models via OpenRouter | 2 | 1 |
| · `openrouter/free` (the router mixed five models in one run) | 1 | 1, every item passed |
| · `nvidia/nemotron-3.5-lightning:free` | 1 | 0, including a fabricated, attributed quote |

Before the final version, 47 more Haiku runs were used during development; each change is
recorded with its before/after counts in [`evals/cheap-model-runs.md`](evals/cheap-model-runs.md).

**Recommended minimum: a Haiku-class model with reliable tool use.** Free models can work end to
end, but reliability varies by model.

What holds: errors come from the models' own sentences, not from the facts the code writes
(numbers, units, directions, verdicts, confidence), which were quoted correctly in almost every
run; the one exception was a Ukrainian answer that added a direction ("+0,7%") to a "no clear
change". Missing or new language editions and follow-up questions were handled in 4 of 4
holdout runs.

## Known limitations

- **Own interpretation.** When asked "why", models sometimes add business reasons the data
  doesn't show ("safe bet", "market saturation"): 4 of the last 7 tuning runs.
- **Topic resolution.** A plural can resolve to a different item ("apples" → the plant genus
  *Malus*), and one holdout run guessed after an `ambiguous` answer (1 of 2).
- **Non-English conversations.** Ukrainian answers didn't say the analyzed article is a proxy
  (2 of 2), and one invented a direction for a stable result.
- **News-driven topics.** On a real news spike (the 2025 papal conclave), the spike was detected
  and confidence was low, but the level-shift reason blamed "search engine changes, bots, a
  rename" for what was the end of a news cycle (2 of 2 holdout runs).
- **One article per language.** Related articles and redirects are not counted; broad intents
  ("learning English") need a proxy article (e.g. the English language), which the answer
  should name.
- **Pageviews only.** Interest on Wikipedia, not willingness to pay or market size; language
  audiences, not countries. Undetected bots can remain in "user" views, especially before 2020.
- Outputs are written inside the skill directory (`output/`), not the user's project.

## How it was built and verified

Built iteratively with Claude Code (plan and history in [`PLAN.md`](PLAN.md)). Every result was
checked outside the model that produced it:

- **By hand, against an independent source** ([`evals/verification-log.md`](evals/verification-log.md)):
  pageviews and totals against pageviews.wmcloud.org, Wikipedia counts against Wikidata. One
  check found a bug (a sister project counted as a Wikipedia), fixed with a regression test;
  another found that Wikimedia's monthly and daily totals can differ slightly (recorded).
- **81 offline tests**, including synthetic series with a known right answer for every trust
  check, and edge cases for every code-written sentence.
- **Calibration on real topics** before fixing thresholds; each wrong answer changed a rule.
- **Cheap-model runs scored with a rubric**, a stopping criterion set before the last tuning
  batch, and a holdout set whose expectations were committed before its runs. Runs are
  reproducible with `uv run --locked python evals/run_scenarios.py H1 H2 --runs 2` (scenarios in
  `evals/scenarios.json`). This needs the Claude Code CLI (`claude`); the skill itself doesn't.
- **A grounding checker** ([`evals/grounding.py`](evals/grounding.py)) that flags quotes and
  numbers not present in what the model received. It caught the fabricated quote and "14 of 12
  months"; on the holdout it had 2 false positives in 14 runs (decimal commas in Ukrainian) and,
  as no answer contained a fabrication, its sensitivity there is unmeasured.

Main lessons (details in `PLAN.md`): code-written facts hold, while the model's own sentences are
where errors appear; short sentences get quoted and long text gets paraphrased; never leave
comparisons for the model to compute; model-side checks fail even when the model sees the
problem, so guards belong in code.

## Repository layout

```
SKILL.md                 agent instructions
setup.sh                 environment setup (uv, or pinned pip fallback)
scripts/wit.py           command line
scripts/wikitrends/      resolve, pageviews, analysis, trust checks, ranking, findings, chart, report
tests/                   offline tests
evals/                   scenarios and runner, rubric, run log, holdout, verification log,
                         grounding checker, transcripts
docs/ROADMAP.md          current state, limitations, next iterations, scaling, evaluation
PLAN.md                  plan, iteration history and design findings
```

## Development

```bash
uv run --locked pytest                 # tests (installs the dev group)
uv run --locked scripts/wit.py --help  # run the CLI

# after changing dependencies:
uv lock
uv export --format requirements-txt --no-dev --no-emit-project -o requirements.txt
```

A test fails if `requirements.txt` is out of sync with `uv.lock`.
