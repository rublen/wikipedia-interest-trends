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
