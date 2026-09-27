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

## Results (2026-09-27, code at `aa7c253`, Claude Haiku 4.5, 2 runs per scenario)

Transcripts: `runs/holdout-H*.md`. Hand scores were recorded before running `grounding.py`.

### The skill

| Scenario | Run 1 | Run 2 | All critical passed | Notes |
|---|---|---|---|---|
| H1 chess, de | pass | pass | 2/2 | minor: scope left out (r1), paraphrased and no chart path (r2) |
| H2 apples, pl+cs, nutrition | pass | **fail** | 1/2 | r1 got `ambiguous`, chose the fruit from context, every item passed. r2 searched the plural **"apples"**, which auto-picked **Malus, the plant genus**; analyzed without comment (G2) |
| H3 Java, no context | **fail** | pass | 1/2 | r1 got `ambiguous` and **guessed** the programming language without saying so (G2); r2 asked and stopped |
| H4 Ukrainian proxy query | **fail** | **fail** | 0/2 | Both translated the intent into the concept themselves (`compare "English language"`), so the English-only guard wasn't needed, and both answered in Ukrainian. But **neither said the article is a proxy**; r1 also invented a direction for German ("**+0,7%**"; its share fell 0.7%), added Russian unasked, and speculated about a cause (G5, G8) |
| H5 pickleball, cs+pl+de | pass | pass | 2/2 | "no article" (pl), "no data a year earlier, new article since 2026-05" (cs, verified), de analyzed, recent July jump called too recent |
| H6 papal conclave, pl+it | **fail** | **fail** | 0/2 | **Skill-side failure** (see below) |
| H7 follow-up (yoga) | pass | pass | 2/2 | turn 2 reran with `--langs uk,pl,de` and `size=0.6,momentum=0.2,confidence=0.2`, stated the weights; r2 reused `--qid` |
| **Total** | | | **8/14** | |

**H6 in detail.** The spike detector worked (spike months Nov 2024–May 2025 in both languages;
the year-earlier period held the *Conclave* film, the Pope's hospital stay, his death and the
conclave: it.wikipedia views 19,559 in March 2025, 212,306 in April, 179,071 in May, 4,055 in
June), and "declining, low confidence" is right. But the **level-shift reason misattributes the
cause**: "views fell abruptly in 2025-06 … jumps this abrupt often have causes outside the topic
(search engine changes, bots, a rename or redirect), so check the article". June 2025 is simply
when the news cycle ended. Both answers relayed this, and r2 concluded "a technical or editorial
event rather than organic interest decline", which is wrong. This technically met the
expectation written above ("low confidence or a flagged level shift"), but that expectation was
too loose: it didn't require the cause to be described correctly. Counted as a failure.

### The grounding checker

| | Count | Detail |
|---|---|---|
| Runs flagged | 2 of 14 | H4 r1, H4 r2 |
| False positives | **2 of 14 runs** | Ukrainian decimal commas: "14,6%" read as "14" (not in the input); same for 10,4 / 41,6 / 35,6 |
| False negatives (invented quote or number missed) | 0 | but no answer contained an invented quote or number, so **sensitivity is not measured** by this holdout |
| Out of scope, as documented | 1 | H4 r1's invented sign "+0,7%" (the number 0.7 is real; signs are ignored) |

### What the holdout shows

1. **Missing and new editions (H5) and follow-ups (H7) are robust: 4/4.** Single-language
   answers (H1) are correct, with minor omissions.
2. **Topic resolution has two blind spots:** plural forms can resolve to a different item
   ("apples" → the genus Malus), and `ambiguous` without context was guessed once in two runs,
   although SKILL.md says to stop. Both are cases where the check belongs in code (finding 6).
3. **Non-English use is the weakest area**, for the skill and the checker alike: proxy not
   stated in either Ukrainian answer, one invented direction, and the checker's decimal-comma
   false positives. The English-only activity guard was not tested in practice, because the
   model translated the query into the concept on its own both times.
4. **Detector wording matters as much as detection:** the level-shift reason lacks "the end of
   a news event", which is the usual cause on news-driven topics, and it sent both answers in
   the wrong direction.
5. As tuned-set runs showed, facts written by code were quoted correctly throughout; the grounding
   checker found no invented quote or number in 14 holdout runs, in line with the hand scores.

These go to the roadmap (not fixed during the holdout, per the protocol): add "the end of a news
event" to the level-shift reason and tell a spike's end apart from a lasting shift; try the
singular form in `resolve` and flag a mismatch; enforce "stop on ambiguous" in code (e.g. no
analysis without `--qid` after an ambiguous answer); state the proxy in the code-written text so
it survives translation; parse decimal commas in the checker.
