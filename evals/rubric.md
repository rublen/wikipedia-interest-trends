# Eval rubric for agent runs

Every agent run (cheap model, full scenario) is scored against this list, so runs are
comparable across iterations. Report results as counts per item ("3/3 quoted the confidence
meaning"), never as "works". Each score needs evidence: a short quote from the transcript.

Score each item **pass**, **fail**, or **n/a** (the item doesn't apply to this run).

## General items

| ID | Item | Pass when |
|---|---|---|
| G1 | Uses the skill | Only the skill's commands were run (no own analysis code), and no tool errors blocked the run |
| G2 | Right topic | The Wikidata item analyzed is the one the user meant, and the answer names it; an ambiguous topic is resolved from context or asked about, never guessed |
| G3 | Numbers from the JSON | Every number in the answer appears in the JSON output (or is a plain restatement, like 559/month); nothing invented |
| G4 | Units | Totals, monthly averages, raw views and share are labelled correctly (e.g. 12-month totals aren't called a monthly average; "share" isn't called "views") |
| G5 | Directions | Every rose/fell, grew/shrank, gained/lost matches the data; no sign misread |
| G6 | Verdict and confidence | Each language's verdict and confidence are stated exactly as in `trend` |
| G7 | Confidence meaning | The meaning of the level is quoted from the summary, not reworded ("weak signal", "real enough to act on" fail) |
| G8 | No invented reasons | Weaknesses or explanations come only from `trend.reasons` / notes (e.g. "seasonal noise" fails: seasonality is controlled) |
| G9 | Scope | The top-level `scope` sentence is quoted once |
| G10 | Next checks, not go/no-go | Recommendations say what to validate next; no "don't build it" / "launch in X" |
| G11 | Chart | The path in `files.chart` is given |

## Scenario items

| ID | Scenario | Pass when |
|---|---|---|
| E1a | Example #1 (pl vs cs, intermittent fasting) | Polish is reported as a finding ("no Polish article, so interest can't be measured there"), not as an error and not left out |
| E2a | Example #2 (astronomy, Ukrainian, "how far can it be trusted?") | The trust question is answered with the verdict, the confidence and its reasons |
| E3a | Example #3 (learning English, 8 languages, report) | The answer and the report say the analyzed article is a **proxy** for "learning English" (and which one) |
| E3b | Example #3 | A report was made (`--report`, `--question`) and `files.report` is given |
| E3c | Example #3 | The `recommendation` lines are quoted (not rewritten into a go/no-go) and the weights used are stated |

## Severity

- **Critical**: a failure would mislead the reader or fail the task: G1, G2, G3, G4, G5, G6,
  G8, G10, E1a, E2a, E3a, E3b.
- **Minor**: quoting or completeness; the answer is still correct: G7, G9, G11, E3c.

Each batch reports, per answer, two rows: **all items passed** and **all critical items
passed**, plus the item counts split by severity.

## How runs are scored

The scorer is the developing agent (Claude) reading each transcript against this rubric,
with every pass/fail backed by a quote; results are recorded in `cheap-model-runs.md`.
Items that can be checked by string matching (G7 exact meaning, G9 scope, G11 chart path)
are checked with `grep` rather than by eye.
