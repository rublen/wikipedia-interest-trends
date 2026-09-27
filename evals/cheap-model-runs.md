# Cheap-model runs

Full scenarios run headless on a cheap model with the skill installed, to find friction
in `SKILL.md` and the CLI output. Transcripts are in `runs/` as Markdown, converted with `transcript.py`; the raw stream-json logs stay local (gitignored) because they contain session metadata.

Local paths in the transcripts are replaced by placeholders (`transcript.py`): `<SKILL_DIR>` is
the installed skill (in these runs a link to this repository), `<SANDBOX>` the empty working
folder the agent ran in, `<repo>` this repository, `~` the home directory.

Runs are produced with `python3 evals/run_scenarios.py <scenario ids> --runs N` (scenarios in
`scenarios.json`); the runs below were made with the same commands typed by hand before the script
existed.

Setup: a scratch directory with `.claude/skills/wikipedia-interest-trends` symlinked to
this repo, `claude -p --model claude-haiku-4-5-20251001 --setting-sources project`
(no personal settings or memory), and an allowlist limited to `Skill`, `Read`,
`SKILL_DIR/setup.sh` and `SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/wit.py`.

## 2026-09-25 — Example #1 (pl vs cs, intermittent fasting), Claude Haiku 4.5

Prompt: "Compare the growth of interest in intermittent fasting in the Polish and Czech
Wikipedia over the last two years."

### Run 1: failed (`runs/2026-09-25-haiku-ex1.md`)
- Loaded the skill, then followed `SKILL.md`: `cd <skill dir> && ./setup.sh`. The `cd` was
  blocked because the skill directory is outside the session's working directory.
- Good: it did not write its own code or invent numbers; it reported that it couldn't run.
- **Root cause (design):** "cd into the skill directory" breaks whenever the skill is
  installed outside the user's project, e.g. in `~/.claude/skills/`, which is the normal case.
- **Fix:** `SKILL.md` now uses absolute paths (`SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/wit.py …`)
  and says not to `cd`. The code already worked from any directory.

### Run 2: passed (`runs/2026-09-25-haiku-ex1-run2.md`)
6 turns, 24 s, $0.036. Skill → `setup.sh` → one `compare` call → read the chart → answer.

| Check | Result |
|---|---|
| Used only the skill's commands | ✅ |
| Polish reported as "no article", not as an error | ✅ |
| All numbers match the JSON (5.81 → 3.08 per million, −47.0%; 4,741 → 2,198, −53.6%; 183/month) | ✅ |
| Caveats: indicative, interest ≠ adoption | ✅ |
| Explained raw vs share difference via cs Wikipedia's −12.6% | ❌ omitted (minor) |

Follow-ups noted:
- Outputs are written inside the skill directory (`output/`); for installed skills they
  should probably go to the user's working directory (Iteration 4).
- Consider making the answer template explicitly mention `project_growth_pct` when raw and
  share growth differ by more than a few points.

## 2026-09-26 — Ambiguous topic "mercury", new `resolution` block, Claude Haiku 4.5

Checks that a small model handles `status: ambiguous` both ways: pick from context when
the context decides, ask when it doesn't.

### A. With context (`runs/2026-09-26-haiku-mercury-context.md`), 6 turns, 26 s, $0.044
Prompt: "We're building a chemistry learning app. Is interest in mercury growing in the
Ukrainian and Polish Wikipedia over the last two years?"

| Check | Result |
|---|---|
| Got `ambiguous`, chose the element Q925 from context and said so | ✅ |
| Numbers copied correctly (pl −20.7% share, −27.7% raw, 3,090/month; uk −37.5%, −52.9%, 823/month) | ✅ |
| Interpretation of `project_growth_pct` | ❌ "even though Polish Wikipedia **grew** overall by 8.8%": the value is **−8.8%** (it shrank). For uk: "despite Ukrainian Wikipedia shrinking only 24.6%", a muddled comparison |

### B. Without context (`runs/2026-09-26-haiku-mercury-nocontext.md`), 5 turns, 25 s, $0.035
Prompt: "How has interest in Mercury changed in the German Wikipedia over the last two years?"

| Check | Result |
|---|---|
| Got `ambiguous`, listed planet / element / Roman god with descriptions and counts | ✅ |
| Stopped to let the user choose | ❌ asked "Which did you mean?", then guessed the planet in the same turn and ran the analysis |
| Numbers and interpretation (share −13.7% vs the whole de Wikipedia −7.3%: lost ground beyond the general decline) | ✅ correct |

### Findings
1. **Sign misreading.** Haiku turned `project_growth_pct: -8.8` into "grew by 8.8%". A
   comparison of three percentages with signs is the kind of reasoning a small model gets
   wrong. Proposed fix: the script writes a plain-language `summary` per language (e.g.
   "the whole Polish Wikipedia shrank 8.8%, so the article's share fell 20.7%") and
   `SKILL.md` says to use it instead of reinterpreting the numbers.
2. **Asks but doesn't wait.** `SKILL.md` says "show candidates and ask", but not "then stop".
   Proposed fix: state explicitly that when the context doesn't decide, the answer ends
   with the question and no analysis is run.
3. The `resolution` block itself worked: in both runs the model used `candidates`
   (description + count) correctly and passed `--qid`.

### After the fixes: same two prompts, run 2

Changes: per-language `summary` and top-level `comparison` sentences written by the script
(directions as words: rose/fell, grew/shrank, gained/lost ground); `SKILL.md` says to use
them, and to stop after asking when the context doesn't decide an ambiguous topic.

**A. With context** (`runs/2026-09-26-haiku-mercury-context-run2.md`), 6 turns, 25 s, $0.038
- ✅ Chose the element Q925 from context; all numbers correct.
- ✅ The sign error is gone: "Polish Wikipedia overall shrank 8.8%", "Ukrainian Wikipedia shrinking 24.6%".
- ⚠️ It paraphrased instead of using the sentences as written and added a misleading
  connective for uk: "its share fell 37.5%, much steeper, **despite** Ukrainian Wikipedia
  shrinking 24.6%". The shrinking wiki is why the share fell *less* than raw views, so
  "despite" doesn't fit. No number is wrong, but the causal wording is.
- ⚠️ It said the output is "in your project directory"; it is in the skill directory
  (known follow-up: output location).

**B. Without context** (`runs/2026-09-26-haiku-mercury-nocontext-run2.md`), 4 turns, 11 s, $0.015
- ✅ Fixed: listed planet / element / Roman god, asked which one, suggested the planet as
  most likely, and **stopped** without running the analysis.

Remaining idea: ask the agent to quote `summary` verbatim (not just "keep direction
words"), since paraphrasing is where the wrong connective came in.

### Run 3: `summary` quoted verbatim

Change: `SKILL.md` now says to quote each `summary` and the `comparison` word for word and
not to add its own explanations ("despite", "because", "reflects").

**A. With context** (`runs/2026-09-26-haiku-mercury-context-run3.md`), 6 turns, 24 s, $0.029
- ✅ Chose the element Q925 from context and said so.
- ✅ Both `summary` sentences and the `comparison` quoted exactly; no misleading
  connectives. Added `avg_monthly_views_recent` for scale as instructed.
- ⚠️ Minor wording in the caveat ("not willingness to market a course") and a closing line
  of its own ("interest… is moving away from both these markets"), consistent with the data.

**B. Without context** (`runs/2026-09-26-haiku-mercury-nocontext-run3.md`), 5 turns, 18 s, $0.021
- ✅ Listed the planet and the element with QIDs, asked which one, and stopped.

Result: both failures from the first mercury runs are fixed. Trade-off: answers are more
formulaic, but every interpretation now comes from tested code.

## 2026-09-26 — Example #2 (astronomy, Ukrainian, "how far can it be trusted?"), Claude Haiku 4.5

First run with Iteration 2 (verdict + confidence + reasons in each `summary`).
Prompt: "We're thinking about adding an astronomy course to our educational app. Is
interest in this topic growing on Ukrainian Wikipedia, and how far can that growth be trusted?"

### Run 1: blocked (`runs/2026-09-26-haiku-ex2.md`)
- `setup.sh` ran with the right path, but then Haiku built the Python path from the session's
  working directory (`sandbox/.venv/bin/python sandbox/scripts/wit.py`), which doesn't exist
  and isn't allowed. It stopped and asked for permission.
- **Root cause:** `setup.sh` printed a *relative* hint (`.venv/bin/python scripts/wit.py`),
  and the model filled in the wrong base directory.
- **Fix:** `setup.sh` now prints the exact absolute command prefix; `SKILL.md` says to copy it.

### Run 2: passed with two issues (`runs/2026-09-26-haiku-ex2-run2.md`), 5 turns, 22 s, $0.025
- ✅ Declining, medium confidence, all four reasons quoted verbatim; answered the actual
  question (it is declining, not growing).
- ⚠️ Invented its own meaning of "medium" ("real enough to act on") and cited "seasonal
  noise" as a weakness, although the year-on-year comparison removes seasonality.
- ⚠️ Gave the CSV path but not the chart.
- **Fix:** `SKILL.md` now gives each confidence level a fixed meaning, says seasonality is
  already handled, and says to always give the chart path.

### Run 3 (`runs/2026-09-26-haiku-ex2-run3.md`), 5 turns, 23 s, $0.026
- ✅ Chart path given; no seasonality claim; verdict and confidence correct. Chose
  `--months 60` on its own (5-year chart, comparison still 12 vs 12): correct use.
- ⚠️ Called "16,614 → 6,708" a *monthly average*; they are 12-month totals (the average is 559).
- **Root cause:** the `summary` gave the totals without a unit.
- **Fix:** the summary now says "… views in total over the 12 compared months".

### Run 4: after the unit fix (`runs/2026-09-27-haiku-ex2-run4.md`), 5 turns, 19 s, $0.032
- ✅ Quoted the summary exactly, including "16,614 → 6,708 views in total over the 12
  compared months"; the totals were not called an average this time.
- ✅ Verdict, confidence and all four reasons verbatim; chart path given; no permission errors.
- ⚠️ Still words the confidence its own way: "medium confidence … a **weak signal** … the
  decline is real enough", instead of the fixed meaning from `SKILL.md` ("probably real,
  but weakened by the reasons listed").
- ⚠️ Ends with a recommendation of its own ("the data argues against pursuing astronomy in
  Ukrainian"), a stronger conclusion than "interest is declining" supports.

### Run 5: confidence meaning written by the script (`runs/2026-09-27-haiku-ex2-run5.md`), 5 turns, 20 s, $0.035
Change: the verdict sentence now includes the fixed meaning of the level ("Verdict: declining,
with medium confidence (probably real, but weakened by the reasons listed). Reasons: …"), and
`SKILL.md` frames recommendations as what to check next, not go/no-go.
- ✅ Quoted the verdict with its meaning verbatim; no invented "weak signal" wording.
- ✅ Explained the medium level with the actual reasons: strong, consistent decline, weakened
  by the small base (~559 views/month).
- ✅ The recommendation stays within the data: "Ukrainian Wikipedia doesn't support that
  hypothesis … check other language editions or markets", not "don't build the course".
- ⚠️ Paraphrased the summary instead of quoting it; the wording stayed correct ("astronomy
  fell much faster" than the whole Wikipedia). One small slip: "10 of 12 months show lower
  **views**"; the check counts the *share*, not raw views.

## 2026-09-27 — Rubric-scored batch: example #2 ×3, example #1 ×1 (regression), Claude Haiku 4.5

Changes before this batch: directions in trust reasons as words ("the share fell 46.4%",
no signed numbers); summary sentence follows a "no clear change" verdict (no "lost ground"
for an 8% move); top-level `scope` sentence, quoted once per answer. First batch scored
against [`rubric.md`](rubric.md). G7, G9 and G11 were checked with `grep` on the final
answer; the rest by reading the transcript. Numbers cited were checked against `result.json`.

Runs: `runs/2026-09-27-haiku-ex2-run6.md`, `-run7.md`, `-run8.md`, `runs/2026-09-27-haiku-ex1-run3.md`.
All 4: 5 turns, 18–21 s, $0.023–0.034, no tool errors.

| Item | ex2 run6 | ex2 run7 | ex2 run8 | ex1 run3 | Count |
|---|---|---|---|---|---|
| G1 Uses the skill | pass | pass | pass | pass | 4/4 |
| G2 Right topic | pass | pass | pass | pass | 4/4 |
| G3 Numbers from the JSON | pass | pass | pass | pass | 4/4 |
| G4 Units | **fail** | pass | pass | pass | 3/4 |
| G5 Directions | pass | pass | pass | pass | 4/4 |
| G6 Verdict and confidence | pass | pass | pass | pass | 4/4 |
| G7 Confidence meaning quoted | pass | **fail** | pass | pass | 3/4 |
| G8 No invented reasons | pass | pass | pass | pass | 4/4 |
| G9 Scope quoted once | pass | **fail** | pass | pass | 3/4 |
| G10 Next checks, not go/no-go | pass | pass | pass (note) | n/a | 3/3 |
| G11 Chart path | pass | pass | **fail** | pass | 3/4 |
| E1a Missing edition reported | – | – | – | pass | 1/1 |
| E2a Trust question answered | pass | pass | pass | – | 3/3 |

Evidence for the failures and notes:
- **G4, run6:** "the article reaches about 9.89 **readers** per million". 9.89 is correct
  (`share_per_million_recent`), but it counts views per million views, not readers.
- **G7, run7:** quoted the meaning in the summary, but the opening line says "the decline
  **is real**, though flagged with medium confidence", which is stronger than "probably real".
- **G9, run7:** no scope sentence; it paraphrased the idea instead ("validate demand through
  other channels before investing heavily").
- **G11, run8:** gave the output folder, not `chart.png`.
- **G10 note, run8:** "falling Wikipedia interest suggests **demand may not be there**" edges
  toward treating interest as demand, but it then quotes the scope sentence and recommends
  validating before dismissing the idea. Scored pass.
- **E1a, ex1 run3:** "Polish Wikipedia: No article is linked to this topic, so interest
  cannot be measured there with this method." The missing-edition path survived the format
  change (regression check passed).

Reading: every failure is a single occurrence, and each is a different item, so none is
systematic yet. What held in 4/4: numbers, directions, verdicts, and no invented reasons,
which are the items the script-written sentences were meant to protect. The fails are
all in the model's *own* sentences around the quotes (openers, labels, omissions).

## 2026-09-27 — Iteration 3 batch: example #3 ×3 (report), regressions #2 ×1 and #1 ×1, Claude Haiku 4.5

New in this batch: `ranking`, `recommendation` and `--report/--question/--note/--weights`.
Prompt #3: "We're building a language-learning app. Compare interest in learning English in our
chosen language editions: Ukrainian, Polish, German, Spanish, Portuguese, Turkish, Japanese and
Vietnamese. Prepare a short report: which audiences should we explore next, and why?"

Runs: `runs/2026-09-27-haiku-ex3-run1.md`, `-run2.md`, `-run3.md`, `runs/2026-09-27-haiku-ex2-run9.md`,
`runs/2026-09-27-haiku-ex1-run4.md`. All: 5 turns, 20–31 s, $0.027–0.047, no tool errors.
All three #3 runs chose on their own `compare "English language" … --report --question … --note "Proxy: …"`.

| Item | #3 r1 | #3 r2 | #3 r3 | #2 r9 | #1 r4 | Count |
|---|---|---|---|---|---|---|
| G1 Uses the skill | pass | pass | pass | pass | pass | 5/5 |
| G2 Right topic | pass | pass | pass | pass | pass | 5/5 |
| G3 Numbers from the JSON | pass | pass | pass | pass | pass | 5/5 |
| G4 Units | pass | pass | pass | pass | **fail** | 4/5 |
| G5 Directions | **fail** | **fail** | **fail** | pass | pass | 2/5 |
| G6 Verdict and confidence | pass | pass | **fail** | pass | pass | 4/5 |
| G7 Confidence meaning quoted | **fail** | pass | **fail** | pass | pass | 3/5 |
| G8 No invented reasons | **fail** | **fail** | pass | pass | pass | 3/5 |
| G9 Scope quoted once | **fail** | pass | **fail** | **fail** | **fail** | 1/5 |
| G10 Next checks, not go/no-go | pass | **fail** | pass | pass | pass | 4/5 |
| G11 Chart path | pass | pass | pass | pass | pass | 5/5 |
| E1a / E2a | – | – | – | pass | pass | 2/2 |
| E3a Proxy stated in the answer | **fail** | **fail** | pass | – | – | 1/3 |
| E3b Report made and given | pass | pass | pass | – | – | 3/3 |
| E3c Recommendation quoted + weights stated | **fail** | **fail** | **fail** | – | – | 0/3 |

Evidence:
- **G5 (3/3 on #3):** vi is "no clear change" (share +1.6%), but r1 says "interest is holding
  steady **or growing**", r3 "the only market where English-language interest **actually grew**";
  r2 says ja is "declining against **platform growth**" (the ja Wikipedia shrank 4.4%).
- **G9 (1/5, down from 3/4):** four runs paraphrased the *old* first `limitations` line
  ("measure curiosity among Wikipedia readers…") instead of quoting `scope`. The JSON contains
  both, nearly identical, and the model picks either.
- **E3c (0/3):** no run stated the ranking weights; r2 and r3 rewrote the recommendation.
- **G8, G10 (r1, r2):** own business reasons: "Ranked #1 **for investment**", "the **safer bet**",
  "**underserved demand**", "**competitive pressure**", "validate whether this reflects
  **seasonal patterns**".
- **G6 (r3):** "Spanish, Polish, Portuguese, Ukrainian: all declining with either medium or low
  confidence"; uk is high.
- **G4 (#1 r4):** "11 of 12 months showed lower **views**" (the check counts share); same slip as ex2 run5.
- **E3a:** the proxy note is in all three PDFs (`--note`), but only r3 said it in the answer.
- Also found: the `comparison` sentence still has signed numbers for tiny changes: "share stayed
  about the same **(-0.7%)**".

## 2026-09-27 — After six fixes: example #3 ×3, regressions #2 ×1 and #1 ×1, Claude Haiku 4.5

Fixes since the previous batch: (1) the duplicate "interest ≠ willingness to pay" limitation
removed, so `scope` is the only wording; (2) a "no clear change" is described by its size
relative to the noise, with no direction ("moved 1.6%, within the ±14% normal fluctuation"),
in every agent-facing text; (3) agent-facing JSON has no signed numbers (changes in words;
the CSV and PDF table keep them); (4) the recommendation includes a "Ranking weights" line;
(5) `--note` is echoed as `topic.note`; (6) `ranking.why` names rank, score, momentum, size and
confidence with the reason that lowered it, plus a SKILL.md rule against own business reasons.

Runs: `runs/2026-09-27-haiku-ex3-run4.md`, `-run5.md`, `-run6.md`, `runs/2026-09-27-haiku-ex2-run10.md`,
`runs/2026-09-27-haiku-ex1-run5.md`. All: 4–5 turns, 20–31 s, $0.036–0.058, no tool errors. All
three #3 runs resolved to Q1860 with `--report --question --note "Proxy: …"`.

| Item | Severity | #3 r4 | #3 r5 | #3 r6 | #2 r10 | #1 r5 | Count | Previous batch |
|---|---|---|---|---|---|---|---|---|
| G1 Uses the skill | critical | pass | pass | pass | pass | pass | 5/5 | 5/5 |
| G2 Right topic | critical | pass | pass | pass | pass | pass | 5/5 | 5/5 |
| G3 Numbers from the JSON | critical | **fail** | pass | pass | pass | pass | 4/5 | 5/5 |
| G4 Units | critical | pass | pass | pass | pass | pass | 5/5 | 4/5 |
| G5 Directions | critical | pass | pass | pass | pass | pass | 5/5 | 2/5 |
| G6 Verdict and confidence | critical | pass | pass | pass | pass | pass | 5/5 | 4/5 |
| G7 Confidence meaning quoted | minor | pass | pass | **fail** | pass | pass | 4/5 | 3/5 |
| G8 No invented reasons | critical | **fail** | **fail** | **fail** | pass | pass | 2/5 | 3/5 |
| G9 Scope quoted once | minor | pass | pass | **fail** | pass | pass | 4/5 | 1/5 |
| G10 Next checks, not go/no-go | critical | pass | pass | pass (note) | pass | n/a | 4/4 | 3/4 |
| G11 Chart path | minor | pass | pass | pass | pass | pass | 5/5 | 5/5 |
| E1a / E2a | critical | – | – | – | pass | pass | 2/2 | 2/2 |
| E3a Proxy stated | critical | pass | pass | pass | – | – | 3/3 | 1/3 |
| E3b Report made and given | critical | pass | pass | pass | – | – | 3/3 | 3/3 |
| E3c Recommendation quoted + weights | minor | pass | pass | **fail** | – | – | 2/3 | 0/3 |
| **All items passed** | | no | no | no | yes | yes | **2/5** | 0/5 |
| **All critical items passed** | | no | no | no | yes | yes | **2/5** | 1/5 |

Failures by severity: critical 4 (previous batch 10), minor 3 (previous 9).

Evidence:
- **G8 (3/3 on #3, a different invention each time):** r4 "Spanish and Portuguese … suggesting
  **market volatility**"; r5 labels language editions as **countries** ("Germany (de)", "Spain
  (es)", "Portugal (pt)"), although Spanish and Portuguese Wikipedia readers are mostly outside
  Spain and Portugal; r6 "75% of views came from detected bots, so **numbers are inflated**"
  (detected bots are already excluded from the counted views), plus "room to grow", "mature audience".
- **G3 (r4):** gives the compared months as "September 2024–August 2025 compared to the same
  months a year earlier"; the recent period is Sep 2025–Aug 2026.
- **G7, G9, E3c (r6):** paraphrased everything (no meaning, no scope sentence, recommendation
  rewritten); it still stated the weights.
- **G10 note (r6):** "Turkish: low-risk expansion candidate if growth is needed" edges toward a
  go decision; the overall recommendation is "validate demand in German and Vietnamese".
- The fixes for signs, directions, proxy and weights held: G5 5/5 (was 2/5), E3a 3/3 (was 1/3),
  E3c weights stated 3/3 (was 0/3), G9 4/5 (was 1/5).

## 2026-09-27 — After three data fixes for G8: example #3 ×3, regressions #2 ×1 and #1 ×1, Claude Haiku 4.5

Fixes: the bot reason says detected bots are "already excluded from these numbers"; a
recommendation line says audiences are language communities, not countries; the "Lower
priority" line gives each language a short reason (verdict, views/month, confidence and its
first reason).

Runs: `runs/2026-09-27-haiku-ex3-run7.md`, `-run8.md`, `-run9.md`, `runs/2026-09-27-haiku-ex2-run11.md`,
`runs/2026-09-27-haiku-ex1-run6.md`. All: 5 turns, 22–30 s, $0.027–0.053, no tool errors.

| Item | Severity | #3 r7 | #3 r8 | #3 r9 | #2 r11 | #1 r6 | Count | Previous batch |
|---|---|---|---|---|---|---|---|---|
| G1 Uses the skill | critical | pass | pass | pass | pass | pass | 5/5 | 5/5 |
| G2 Right topic | critical | pass | pass | pass | pass | pass | 5/5 | 5/5 |
| G3 Numbers from the JSON | critical | **fail** | **fail** | pass | pass | pass | 3/5 | 4/5 |
| G4 Units | critical | pass | pass | pass | **fail** | pass | 4/5 | 5/5 |
| G5 Directions | critical | pass | **fail** | pass | pass | pass | 4/5 | 5/5 |
| G6 Verdict and confidence | critical | pass | **fail** | pass | pass | pass | 4/5 | 5/5 |
| G7 Confidence meaning quoted | minor | **fail** | pass | **fail** | **fail** | pass | 2/5 | 4/5 |
| G8 No invented reasons | critical | **fail** | pass (note) | **fail** | **fail** | pass | 2/5 | 2/5 |
| G9 Scope quoted once | minor | **fail** | pass | pass | **fail** | **fail** | 2/5 | 4/5 |
| G10 Next checks, not go/no-go | critical | **fail** | pass | **fail** | pass | n/a | 2/4 | 4/4 |
| G11 Chart path | minor | pass | pass | pass | **fail** | pass | 4/5 | 5/5 |
| E1a / E2a | critical | – | – | – | pass | pass | 2/2 | 2/2 |
| E3a Proxy stated | critical | pass | pass | pass | – | – | 3/3 | 3/3 |
| E3b Report made and given | critical | pass | pass | pass | – | – | 3/3 | 3/3 |
| E3c Recommendation quoted + weights | minor | **fail** | **fail** | **fail** | – | – | 0/3 | 2/3 |
| **All items passed** | | no | no | no | no | no | **0/5** | 2/5 |
| **All critical items passed** | | no | no | no | no | yes | **1/5** | 2/5 |

Failures by severity: critical 10 (previous 4), minor 10 (previous 3). **A regression.**

What the targeted fixes did:
- Countries: fixed (0/3 runs used country names; previous batch 1/3).
- Bots: 2/3 now correct ("suggests some undetected bots remain"); r7 still says the bot share
  "may inflate or distort the signal".
- Lower-priority reasons: the models still added their own: r7 "market saturation, app
  availability"; r9 "a ready market to test", "riskier to enter now".

New and repeated failures:
- **G3 (r7, r8):** "Turkish (stable, smallest audience)"; Ukrainian is the smallest. The new
  "Lower priority" line gives views/month but no size rank, and both runs inferred it wrongly.
- **G5, G6 (r8):** "Japanese (stable in share but declining overall)" (its share fell 11.0%);
  "Polish and Portuguese (declining; low confidence)" (Polish is medium).
- **G10 (r7, r9):** "strongest expansion candidates", "may still justify entry", "riskier to enter now".
- **G7, G9, E3c:** more paraphrasing than before in 3–4 of 5 runs; E3c 0/3.
- **G4 (#2 r11):** "10 out of 12 months showed fewer **views**" (the check counts share); the third
  run with this exact slip (after ex2 run5 and ex1 run4).

Reading: the answers got longer and more paraphrased. One plausible cause is that the
recommendation grew (six per-language reasons plus the audiences line), and a longer text to
quote is paraphrased more. Run-to-run variance with 3 runs per scenario is also large, so this
batch alone can't separate the two.

## 2026-09-27 — Controlled test: short recommendation + "share" wording; example #3 ×5, #2 ×1, #1 ×1

Stopping criterion (set in `PLAN.md` before this batch): all critical items pass in ≥ 4 of 5
runs of example #3, with no critical failure in the #1 and #2 regression runs.

Changes (two only): the "Lower priority" line is a plain list again (the per-language reasons
from the previous batch are removed; the bot and countries fixes stay); the consistency reason
names the metric ("the share was lower than in the same month a year earlier in 10 of 12 months").

Runs: `runs/2026-09-27-haiku-ex3-run10.md` … `-run14.md`, `runs/2026-09-27-haiku-ex2-run12.md`,
`runs/2026-09-27-haiku-ex1-run7.md`. All: 4–5 turns, 18–30 s, $0.025–0.042, no tool errors.
Answer length for #3: median 371 words (previous batch: 537).

| Item | Severity | #3 r10 | #3 r11 | #3 r12 | #3 r13 | #3 r14 | #2 r12 | #1 r7 | Count |
|---|---|---|---|---|---|---|---|---|---|
| G1 Uses the skill | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 |
| G2 Right topic | critical | pass | pass | pass | pass | **fail** | pass | pass | 6/7 |
| G3 Numbers from the JSON | critical | pass | pass | pass | **fail** | pass | pass | pass | 6/7 |
| G4 Units | critical | pass | pass | pass | **fail** | pass | pass | pass | 6/7 |
| G5 Directions | critical | **fail** | **fail** | pass | **fail** | pass | pass | pass | 4/7 |
| G6 Verdict and confidence | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 |
| G7 Confidence meaning quoted | minor | **fail** | **fail** | **fail** | pass | pass | pass | pass | 4/7 |
| G8 No invented reasons | critical | pass | pass | **fail** | pass | pass | **fail** | pass | 5/7 |
| G9 Scope quoted once | minor | pass | pass | **fail** | pass | pass | **fail** | pass | 5/7 |
| G10 Next checks, not go/no-go | critical | pass | pass | pass | pass | pass | pass | n/a | 6/6 |
| G11 Chart path | minor | pass | pass | pass | pass | pass | **fail** | pass | 6/7 |
| E1a / E2a | critical | – | – | – | – | – | pass | pass | 2/2 |
| E3a Proxy stated | critical | pass | pass | pass | pass | **fail** | – | – | 4/5 |
| E3b Report made and given | critical | pass | pass | pass | pass | pass | – | – | 5/5 |
| E3c Recommendation quoted + weights | minor | **fail** | **fail** | **fail** | **fail** | pass | – | – | 1/5 |
| **All items passed** | | no | no | no | no | no | no | yes | **1/7** |
| **All critical items passed** | | no | no | no | no | no | no | yes | **1/7** |

**Stopping criterion: not met** (#3 critical pass 0/5; #2 regression failed on G8).

Evidence:
- **G5 (r10, r11, r13): cross-language grouping done by the model.** r10: "All six others show
  declining interest (Polish, Spanish, Portuguese, **Turkish**, Ukrainian…)"; Turkish is "no
  clear change". r11: "Vietnamese offers high-confidence **growth**". r13: "Japanese … losing
  mindshare **fastest**" (Ukrainian fell most) and "Portuguese and Spanish also show **stable**
  patterns".
- **G3, G4 (r13):** "German … the **only** cohort member holding attention steady" (vi and tr are
  stable too); "Turkish … **smallest** audience" (Ukrainian is); "10–15 **percentage point** drops"
  (they are percent changes).
- **G2, E3a (r14):** searched "Learning English", accepted the auto-picked Voice of America
  programme ("The 'Learning English' article (Voice of America's simplified English program)")
  and ran the whole analysis on it, although `SKILL.md` names this exact case.
- **G8:** r12 "Ukrainian … steepest decline, **suggesting the smallest addressable audience**";
  #2 r12 "**a few schools adding/removing the article to curricula** could shift these numbers".
- **G7 (r11):** gave German's *medium* level the *high* meaning ("the data consistently shows this").
- **Held:** G4 "views vs share" is fixed at the source (both regression runs: "the share was lower
  than a year earlier in … months"); no country names; no "numbers inflated by bots"; G10 6/6.

Reading: shortening worked on length, not on errors. Nearly every remaining critical failure in
#3 is a statement *across languages* that the model worked out itself: which languages are
stable or declining, which is smallest, which fell fastest, which is the "only" one. No field
states these, so the model computes them from eight per-language entries and gets them wrong.
That is principle 2 ("never hand the model data it has to compare or rank") at the level of the
whole answer.

## 2026-09-27 — Final tuning batch: `key_findings`; example #3 ×5, #2 ×1, #1 ×1

Change: `key_findings`, 5–7 short sentences with every cross-language claim precomputed (groups
with explicit "none", largest/smallest audience, steepest change, ranking with weights,
low-confidence languages, not-measurable languages), led by "Analyzing: <label> (<QID>),
<description>" so a wrong topic shows in one line. `SKILL.md`: start from them; cross-language
statements only from them; stop if "Analyzing" isn't what the user means. This was declared
the last tuning batch in advance, whatever the result.

Runs: `runs/2026-09-27-haiku-ex3-run15.md` … `-run19.md`, `runs/2026-09-27-haiku-ex2-run13.md`,
`runs/2026-09-27-haiku-ex1-run8.md`. 4–5 turns, 19–30 s, $0.027–0.045. One tool error (r18:
`bash setup.sh` inside a compound command needed approval; it recovered on the next call).

| Item | Severity | #3 r15 | #3 r16 | #3 r17 | #3 r18 | #3 r19 | #2 r13 | #1 r8 | Count |
|---|---|---|---|---|---|---|---|---|---|
| G1 Uses the skill | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 |
| G2 Right topic | critical | pass | **fail** | pass | pass | pass | pass | pass | 6/7 |
| G3 Numbers from the JSON | critical | pass | pass | **fail** | **fail** | pass | pass | pass | 5/7 |
| G4 Units | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 |
| G5 Directions | critical | **fail** | pass | pass | pass | pass | pass | pass | 6/7 |
| G6 Verdict and confidence | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 |
| G7 Confidence meaning quoted | minor | **fail** | **fail** | **fail** | **fail** | **fail** | pass | pass | 2/7 |
| G8 No invented reasons | critical | **fail** | pass | **fail** | pass | pass | pass | **fail** | 4/7 |
| G9 Scope quoted once | minor | **fail** | **fail** | **fail** | pass | **fail** | **fail** | pass | 2/7 |
| G10 Next checks, not go/no-go | critical | pass | pass | pass | pass | **fail** | pass | n/a | 5/6 |
| G11 Chart path | minor | pass | pass | **fail** | pass | pass | pass | **fail** | 5/7 |
| E1a / E2a | critical | – | – | – | – | – | pass | pass | 2/2 |
| E3a Proxy stated | critical | pass | **fail** | pass | pass | pass | – | – | 4/5 |
| E3b Report made and given | critical | pass | pass | **fail** | pass | pass | – | – | 4/5 |
| E3c Recommendation quoted + weights | minor | **fail** | **fail** | **fail** | pass | **fail** | – | – | 1/5 |
| **All items passed** | | no | no | no | no | no | no | no | **0/7** |
| **All critical items passed** | | no | no | no | no | no | yes | no | **1/7** |

**Stopping criterion: not met** (#3 critical pass 0/5, same as the previous batch). Per the
rule set before the batch, tuning stops here; the remaining failures are recorded as known
limitations in `PLAN.md`.

**`key_findings` were not used:** 0 of 7 answers quoted the groups sentence or the
"Analyzing" line. Answers still made their own cross-language claims, and they were still the
main critical errors: r17 "German and Vietnamese … the **only two** where interest didn't lose
ground" (Turkish too); r15 lists Turkish among audiences that "all show **downward** momentum"
and calls Vietnamese a "**growing** absolute interest base" (its views fell 23.1%); r18 swaps
the numbers ("Polish and Ukrainian's declines, **14.6% and 10.4%** respectively"; it is the
other way round).

Evidence for the other failures:
- **G2, E3a (r16):** searched "learning English" and analyzed the Voice of America programme
  again, describing it correctly ("Voice of America's 'Learning English' (a simplified-English
  program)") and still calling it a proxy. Second occurrence in 10 runs; making the entity
  visible was not enough.
- **G8:** r15 "75% of views in one period were bot traffic, which may **inflate** some months";
  r17 "stable interest in a **growing market**"; #1 r8 "not just **seasonal** spikes".
- **G10 (r19):** "Declining audiences (**avoid for now**)".
- **G7, G9:** meaning and scope paraphrased in 5 of 7 answers; r18 gave German's *medium* level
  the *high* meaning again ("German's stability is real (the data consistently shows this)").

**Likely cause (hypothesis, untested because this was the last batch):** the agent-facing JSON
for 8 languages is about 5,300 tokens, most of it per-language detail, and `SKILL.md` (1,095
words) asks both to "start from `key_findings`" and to quote every language's `summary`. The
model follows the more detailed per-language instruction and writes its own connecting
sentences between the quotes.

## 2026-09-27 — Last batch: compact output + activity-phrase guard; example #3 ×5, #2 ×1, #1 ×1

Changes (fixing a known contradiction, not tuning): for more than 2 measurable languages the
default output has `key_findings`, `comparison`, one code-written `line` per language and the
recommendation, without per-language summaries (~1,800 tokens instead of ~5,300; full detail in
`files.result` or with `--details`); `resolve` never auto-picks an activity phrase ("learning X",
"X courses"); SKILL.md answer section rewritten as one ordered list without competing
instructions, with bounded retries (960 words, was 1,095).

Runs: `runs/2026-09-27-haiku-ex3-run20.md` … `-run24.md`, `runs/2026-09-27-haiku-ex2-run14.md`,
`runs/2026-09-27-haiku-ex1-run9.md`. 4–5 turns, 22–29 s, $0.025–0.032, no tool errors. All
five #3 runs searched "English language" directly.

| Item | Severity | #3 r20 | #3 r21 | #3 r22 | #3 r23 | #3 r24 | #2 r14 | #1 r9 | Count | Previous |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 Uses the skill | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 | 7/7 |
| G2 Right topic | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 | 6/7 |
| G3 Numbers from the JSON | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 | 5/7 |
| G4 Units | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 | 7/7 |
| G5 Directions | critical | pass | pass | pass | pass | pass | pass | pass | 7/7 | 6/7 |
| G6 Verdict and confidence | critical | pass | **fail** | pass | pass | pass | pass | pass | 6/7 | 7/7 |
| G7 Confidence meaning quoted | minor | **fail** | **fail** | **fail** | **fail** | **fail** | pass | **fail** | 1/7 | 2/7 |
| G8 No invented reasons | critical | **fail** | **fail** | **fail** | pass | pass | pass | **fail** | 3/7 | 4/7 |
| G9 Scope quoted once | minor | pass | pass | pass | pass | pass | pass | pass | 7/7 | 2/7 |
| G10 Next checks, not go/no-go | critical | pass | pass | pass | pass | pass | pass | n/a | 6/6 | 5/6 |
| G11 Chart path | minor | pass | pass | pass | pass | pass | **fail** | pass | 6/7 | 5/7 |
| E1a / E2a | critical | – | – | – | – | – | pass | pass | 2/2 | 2/2 |
| E3a Proxy stated | critical | pass | pass | pass | pass | pass | – | – | 5/5 | 4/5 |
| E3b Report made and given | critical | pass | pass | pass | pass | pass | – | – | 5/5 | 4/5 |
| E3c Recommendation quoted + weights | minor | **fail** | pass | pass | pass | **fail** | – | – | 3/5 | 1/5 |
| **All items passed** | | no | no | no | no | no | no | no | **0/7** | 0/7 |
| **All critical items passed** | | no | no | no | **yes** | **yes** | **yes** | no | **3/7** | 1/7 |

Failures by severity: critical 5 (previous 10), minor 9 (previous 16).
**Stopping criterion: not met** (#3 critical pass 2/5, target ≥ 4/5). As agreed, this was the
last batch.

What changed:
- **`key_findings` are now quoted:** the groups sentence and "Largest audience" in 5/5 #3
  answers (0/7 before). Wrong cross-language claims dropped to one answer (r21, "lowest
  confidence", scored under G6); G3 and G5 were 7/7 (before, these were the main critical errors).
- **Scope quoted 7/7** (2/7 before); no wrong topic; every #3 run went straight to "English language".

Remaining failures:
- **G8 (4 of 7), all in the model's own "why" paragraphs after the quotes:** r20 "may need
  **product differentiation to retain users**"; r21 "a **safe bet**", "**hidden opportunity**",
  "**early-adopter demand**", "a **saturated** or shifting market"; r22 "no deterioration suggests
  **sustained demand**"; #1 r9 rewrote the confidence reason as "weakened by … **month-to-month
  variation**" (the noise check supported the verdict; it wasn't a weakness).
- **G6 (r21):** "Ukrainian and Portuguese show the steepest declines and **lowest confidence**";
  Ukrainian is high confidence.
- **G7 (6 of 7):** the per-language `line` was quoted without its bracketed confidence meaning.
- **G11 (#2 r14), E3c (r20, r24):** chart path missing; recommendation shortened or weights left out.

Reading: moving the comparisons into code and removing the competing text fixed the
cross-language errors. What remains is the model's own interpretation when the user asks
"why" — the one part of the answer the script doesn't write. That is what a ready-to-quote
answer (roadmap) would address.

## 2026-09-27 — User-driven runs (holdout wording): Haiku via Claude Code, free models via OpenRouter

Driven by the user in their own Claude Code sessions (skill installed as
`~/.claude/skills/wikipedia-interest-trends`, empty working folder), with **their own prompt**,
not one the format was tuned on:

> Compare interest in "English language" learning topic across Wikipedia editions: Ukrainian,
> Polish, German, Spanish, Portuguese, Turkish, Japanese, and Vietnamese. Provide insights on
> which audiences have highest interest and growth potential for a language-learning app.

Three sessions; two are scored:
- `runs/2026-09-27-user-haiku-claude-code.md`: **Claude Haiku 4.5**, the user's Claude account.
- `runs/2026-09-27-user-openrouter-free.md`: **`openrouter/free`** through OpenRouter's
  Anthropic-compatible endpoint. The router switched between **five free models within the run**
  (setup, both `compare` calls and the final answer came from different models; the final answer
  from dots-studio/dots-3-note-preview), so it tests "some free model", not one model.
- Not scored: a third session with `anthropic/claude-haiku-4.5` via OpenRouter stopped at
  `402 Insufficient credits` before any model answered (setup check only).

| Item | Severity | Haiku (Claude Code) | Free models (OpenRouter) |
|---|---|---|---|
| G1 Uses the skill | critical | pass | pass |
| G2 Right topic | critical | pass | pass |
| G3 Numbers from the JSON | critical | **fail** | pass |
| G4 Units | critical | pass | pass |
| G5 Directions | critical | pass | pass |
| G6 Verdict and confidence | critical | pass | pass |
| G7 Confidence meaning quoted | minor | pass | pass |
| G8 No invented reasons | critical | **fail** | pass |
| G9 Scope quoted once | minor | pass | pass |
| G10 Next checks, not go/no-go | critical | pass | pass |
| G11 Chart path | minor | pass | pass |
| E3a Proxy stated | critical | pass | pass |
| E3b Report made and given | critical | pass | pass |
| E3c Recommendation quoted + weights | minor | pass | pass |
| **All items passed** | | no | **yes** |
| **All critical items passed** | | no | **yes** |

Evidence:
- **Haiku, G3:** "German has the **largest audience size** (3rd overall)": German is the 3rd
  largest; the sentence contradicts itself and `key_findings` (largest: ja).
- **Haiku, G8:** "declining interest suggests potential **market saturation or shifting user
  behavior**"; the same kind of own "why" as in the last tuning batch.
- **Haiku, otherwise:** quoted all key findings, the comparison, every confidence meaning (in a
  table), the full recommendation with weights and the scope sentence.
- **Free models:** quoted everything in order (key findings, comparison, every per-language line
  with its meaning, recommendation, weights, scope) and wrote a "bottom line" built only from
  those facts ("German and Vietnamese … both are stable with the largest audiences among the
  stable group"; "Spanish and Portuguese declines are low-confidence and driven by a few unusual
  months"). The first `compare` call left out `--report`; the next model reran it with `--report
  --question --note`.

Reading: with a new wording, the same pattern as the last tuning batch: code-written facts
quoted correctly by both; the only failures are in Haiku's own interpretation paragraph. The
free-model run passing every item is one run with a router mixing five models, so it shows the
skill *can* work end to end on free models, not how reliably.

### User-driven run: one pinned free model, `nvidia/nemotron-3.5-lightning:free` via OpenRouter

`runs/2026-09-27-user-openrouter-nemotron.md`. Same prompt as above; a single model for the whole
run (7 replies), no tool errors; ran `compare "English language" --langs uk,pl,de,es,pt,tr,ja,vi`
without `--report` or `--note` (the prompt didn't ask for a report, so E3b is n/a).

| Item | Severity | Result | Evidence |
|---|---|---|---|
| G1 Uses the skill | critical | pass | skill → `compare` (setup already done) |
| G2 Right topic | critical | pass | Q1860 |
| G3 Numbers / facts from the JSON | critical | **fail** | **invented quotation with attribution:** *"No language showed actual growth in share … The 'stable' ones … represent the most reliable audiences for a language-learning app." — recommendation* (checked: not in the output); "vi: **highest confidence of all languages**" (tr, ja and uk are high too); "pl & uk: **smallest audiences**" (tr is smaller than pl); "uk: share fell in **14 of 12 months**?" |
| G4 Units | critical | pass | |
| G5 Directions | critical | pass | |
| G6 Verdict and confidence | critical | pass | per-language table correct |
| G7 Confidence meaning quoted | minor | **fail** | not included |
| G8 No invented reasons | critical | **fail** | "Southeast Asian market with **growing English learning demand**"; "may indicate **market saturation**"; "**consider localization**" |
| G9 Scope quoted once | minor | pass | quoted |
| G10 Next checks, not go/no-go | critical | **fail** | "Both should be **deprioritized for new app features**"; a Primary/Secondary/Deprioritize table |
| G11 Chart path | minor | **fail** | no files given |
| E3a Proxy stated | critical | **fail** | no proxy note, not mentioned |
| E3b Report | critical | n/a | not requested |
| E3c Recommendation quoted + weights | minor | **fail** | weights stated; recommendation partly quoted plus the invented quote above |
| **All critical items passed** | | **no** | |

Confirmed mechanically with `evals/grounding.py` (added afterwards): 1 ungrounded quote (the
invented one) and 1 ungrounded number phrase ("14 of 12"); the Haiku and `openrouter/free`
user runs and the 7 last-batch runs have none. The Haiku G3 failure ("largest audience (3rd
overall)") is not caught: its numbers are right, the word "largest" is wrong.

New failure type: **a fabricated quote in quotation marks, attributed to the tool output.** Quote
marks alone don't prove a quote is real. This can be checked mechanically: every quoted string in
an answer should appear verbatim in the JSON the model received (see roadmap: automatic quote check).
It also qualifies the earlier `openrouter/free` result: that run's final answer came from a
different free model (dots-3-note), and free models clearly differ in how faithfully they quote.
