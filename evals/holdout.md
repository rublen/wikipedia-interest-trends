# Holdout set

Scenarios the answer format was **never tuned on**, to measure the skill, and the grounding
checker, on data and wording they weren't calibrated on.

## Protocol (fixed before any holdout run)

- **Code frozen** at commit `aa7c253` (skill, SKILL.md and `evals/grounding.py`). No changes
  during the holdout; problems found go to the results and the roadmap.
- **Expectations written first** (this file, committed before the runs). They describe the
  correct behavior and, where outside knowledge allows, the correct facts.
- **Each scenario runs twice** on Claude Haiku 4.5 (headless, same sandbox and allowlist as in
  `cheap-model-runs.md`), so a failure can be told apart from one bad run.
- **Scoring order:** (1) rubric by hand, including my own check of quotes and numbers;
  (2) only then `evals/grounding.py`. Its results are compared with the hand scores:
  *false positive* = flagged but judged honest; *false negative* = an invented quote or number
  it missed.
- Reported per scenario and in total: all-critical-passed counts for the skill; FP/FN counts
  for the checker.

## Scenarios and expectations

### H1 — Single language, plain topic
Prompt: "Is interest in chess growing on German Wikipedia?"
- Resolves to chess (Q718) without asking. One language, so the full `summary` is output.
- The answer states the verdict and confidence exactly as the tool gives them, quotes the
  summary, gives the chart path and the scope sentence. No own business reasons.

### H2 — Ambiguous topic, context decides
Prompt: "We make nutrition content for Polish and Czech readers. Compare interest in apples in
the Polish and Czech Wikipedia over the last two years."
- "apple" may resolve to the fruit or the company. The fruit is correct (context: nutrition).
  If the tool returns `ambiguous`, the agent picks the fruit with `--qid` and says so; if it
  auto-picks, the item must be the fruit. Analyzing Apple Inc. is a G2 fail.

### H3 — Ambiguous topic, no context
Prompt: "How has interest in Java changed on Polish Wikipedia?"
- Java is an island, a programming language, coffee… With no context, the correct behavior is
  to **stop and ask** which one, listing candidates, and not to run the analysis on a guess
  (unless the tool auto-picks, in which case the answer must name the item it analyzed).

### H4 — Proxy intent, asked in Ukrainian (blind spot of the activity-phrase guard)
Prompt: "Чи зростає інтерес до вивчення англійської мови в українській Вікіпедії? Ми думаємо
про курс англійської для українців."
- The guard is an English regex, so a Ukrainian query can bypass it. Correct: the analyzed
  item is a concept that stands for the interest (e.g. the English language, Q1860) and the
  answer says it is a proxy. Analyzing the Voice of America "Learning English" programme or a
  similar niche item is a G2 fail.
- Expected, though not a rubric item: the answer is in Ukrainian.

### H5 — Several languages with missing or new editions
Prompt: "Compare interest in pickleball in the Czech, Polish and German Wikipedia."
- From calibration (2026-09-26): pl has no article; cs has too little data a year earlier.
  Correct: pl reported as "no article" (a finding), cs as not comparable / insufficient data or
  a new article, de analyzed normally. No ranking claims across unmeasurable languages.

### H6 — Genuine news spike (detectors on data they weren't calibrated on)
Prompt: "Is interest in papal conclaves growing in the Polish and Italian Wikipedia?"
- Outside knowledge: Pope Francis died on 21 April 2025 and the conclave was held on 7–8 May
  2025, so views of the conclave article should **spike in April–May 2025**, in the year-earlier
  period of a 24-month comparison. Expected from the detectors: spike months 2025-04 and/or
  2025-05 flagged, and the verdict **not** presented as a steady trend: either "declining" with
  **low** confidence ("the change comes from a few unusual months") or a flagged level shift.
  A high-confidence "declining" with no mention of the spike is a detector failure.
- The answer must not invent the cause (the tool doesn't know about the conclave); stating it
  as outside context is acceptable only if marked as such.

### H7 — Follow-up question in the same conversation
Turn 1: "Compare interest in yoga in the Ukrainian and Polish Wikipedia."
Turn 2: "Now add German, and weight audience size more than momentum."
- Turn 2 reruns `compare` with `--langs uk,pl,de` (reusing the QID) and weights that put size
  above momentum (e.g. `size=0.6,momentum=0.2,confidence=0.2`), and states the weights used.
  Three languages, so the compact output applies.
