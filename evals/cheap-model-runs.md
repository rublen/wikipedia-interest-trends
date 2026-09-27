# Cheap-model runs

Full scenarios run headless on a cheap model with the skill installed, to find friction
in `SKILL.md` and the CLI output. Transcripts are in `runs/` as Markdown, converted with `transcript.py`; the raw stream-json logs stay local (gitignored) because they contain session metadata.

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
