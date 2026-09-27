# Run: 2026-09-27-user-openrouter-free (driven by the user in Claude Code)

**Model:** `openrouter/free` via OpenRouter's Anthropic-compatible endpoint; the router used five free models in this one run: poolside/laguna-xs-2.1 (setup), nvidia/nemotron-3.5-lightning (first compare), inclusionai/ling-3.0-flash-fin (compare with report), dots-studio/dots-3-note-preview (final answer), plus inclusionai/ling-3.0-flash-sante

**Prompt:** Compare interest in "English language" learning topic across Wikipedia editions: Ukrainian, Polish, German, Spanish, Portuguese, Turkish, Japanese, and Vietnamese. Provide insights on which audiences have highest interest and growth potential for a language-learning app.

### User

Compare interest in "English language" learning topic across Wikipedia editions: Ukrainian, Polish, German, Spanish,
  Portuguese, Turkish, Japanese, and Vietnamese. Provide insights on which audiences have highest interest and growth
  potential for a language-learning app.

**Tool call — Skill:**

```json
{
 "skill": "wikipedia-interest-trends"
}
```

<details><summary>Tool result</summary>

```
Launching skill: wikipedia-interest-trends
```
</details>

### Assistant

Let me set up the skill first and then run the analysis for English language learning interest across the specified Wikipedia editions.

**Tool call — Bash:**

```json
{
 "command": "SKILL_DIR=<SKILL_DIR> && $SKILL_DIR/setup.sh",
 "description": "Setup the Wikipedia interest trends skill"
}
```

<details><summary>Tool result</summary>

```
setup: using uv (uv 0.12.18 (Homebrew 2026-09-22 aarch64-apple-darwin))
setup: OK - run the skill with exactly this command prefix:
<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py
```
</details>

### Assistant

Now let me run the comparison for the English language topic across the specified Wikipedia editions:

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py compare \"English language\" --langs uk,pl,de,es,pt,tr,ja,vi --months 24",
 "description": "Compare English language interest across Wikipedia editions"
}
```

<details><summary>Tool result</summary>

```
{
 "status": "ok",
 "topic": {
  "query": "English language",
  "qid": "Q1860",
  "label": "English",
  "description": "West Germanic language",
  "note": null,
  "resolution": {
   "method": "search",
   "decision": "auto_picked",
   "reason": "the first search result with articles is also the most-linked item, with 2.44x the Wikipedias of the runner-up (Q328 English Wikipedia)",
   "rule": "auto-pick only if the first search result with Wikipedia articles is also the item with the most articles, with at least 2x the runner-up",
   "best": {
    "qid": "Q1860",
    "label": "English",
    "wikipedias": 317
   },
   "runner_up": {
    "qid": "Q328",
    "label": "English Wikipedia",
    "wikipedias": 130
   },
   "ratio": 2.44,
   "candidates": [
    {
     "search_rank": 1,
     "qid": "Q1860",
     "label": "English",
     "description": "West Germanic language",
     "wikipedias": 317
    },
    {
     "search_rank": 2,
     "qid": "Q328",
     "label": "English Wikipedia",
     "description": "English-language edition of Wikipedia",
     "wikipedias": 130
    },
    {
     "search_rank": 3,
     "qid": "Q27968",
     "label": "English studies",
     "description": "discipline that studies the English language and literature",
     "wikipedias": 31
    },
    {
     "search_rank": 4,
     "qid": "Q186579",
     "label": "English-language literature",
     "description": "literary works written in the English language",
     "wikipedias": 76
    },
    {
     "search_rank":
… [6899 more chars]
```
</details>

### Assistant

I have the core data. Let me now generate a report with the analysis question for a more complete deliver

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py compare \"English language\" --langs uk,pl,de,es,pt,tr,ja,vi --months 24 --report --question \"Which audiences have highest interest and growth potential for a language-learning app?\" --note \"Proxy: the article on the English language (Q1860), read in each audience's own Wikipedia edition.\"",
 "description": "Generate a report on English language interest across Wikipedia editions"
}
```

<details><summary>Tool result</summary>

```
{
 "status": "ok",
 "topic": {
  "query": "English language",
  "qid": "Q1860",
  "label": "English",
  "description": "West Germanic language",
  "note": "Proxy: the article on the English language (Q1860), read in each audience's own Wikipedia edition.",
  "resolution": {
   "method": "search",
   "decision": "auto_picked",
   "reason": "the first search result with articles is also the most-linked item, with 2.44x the Wikipedias of the runner-up (Q328 English Wikipedia)",
   "rule": "auto-pick only if the first search result with Wikipedia articles is also the item with the most articles, with at least 2x the runner-up",
   "best": {
    "qid": "Q1860",
    "label": "English",
    "wikipedias": 317
   },
   "runner_up": {
    "qid": "Q328",
    "label": "English Wikipedia",
    "wikipedias": 130
   },
   "ratio": 2.44,
   "candidates": [
    {
     "search_rank": 1,
     "qid": "Q1860",
     "label": "English",
     "description": "West Germanic language",
     "wikipedias": 317
    },
    {
     "search_rank": 2,
     "qid": "Q328",
     "label": "English Wikipedia",
     "description": "English-language edition of Wikipedia",
     "wikipedias": 130
    },
    {
     "search_rank": 3,
     "qid": "Q27968",
     "label": "English studies",
     "description": "discipline that studies the English language and literature",
     "wikipedias": 31
    },
    {
     "search_rank": 4,
     "qid": "Q186579",
     "label": "English-language literature",
     "description": "literar
… [7185 more chars]
```
</details>

**Tool call — Read:**

```json
{
 "file_path": "<repo>/output/Q1860-english/chart.png"
}
```

<details><summary>Tool result</summary>

```
[image]
```
</details>

### Assistant

## English Language Interest Across Wikipedia Editions

### What was measured

"Analyzing: "English" (Q1860), West Germanic language. Proxy: the article on the English language (Q1860), read in each audience's own Wikipedia edition."

The comparison is **last 12 complete months (2025-09..2026-08) vs the same months a year earlier (2024-09..2025-08)**, so seasonal effects cancel out. The chart spans 2024-09..2026-08.

### Key findings

- Growing: none. Stable (no clear change): de, vi and tr. Declining: ja, es, pl, uk and pt.
- Largest audience: ja (36,383 views/month); smallest: uk (6,659 views/month).
- Strongest growth in share: none. Steepest decline in share: uk (fell 14.6%).
- Ranked first: de, then vi (weights: momentum 0.4, size 0.4, confidence 0.2).
- Low confidence, don't rely on these alone: es and pt.

### Comparison

By change in share of attention, strongest first: de (share moved 0.7%, within the ±4% normal fluctuation, no clear change with medium confidence); tr (share moved 0.2%, within the ±13% normal fluctuation, no clear change with high confidence); vi (share moved 1.6%, within the ±14% normal fluctuation, no clear change with high confidence); pl (share fell 10.4%, declining with medium confidence); es (share fell 10.4%, declining with low confidence); ja (share fell 11.0%, declining with high confidence); pt (share fell 11.2%, declining with low confidence); uk (share fell 14.6%, declining with high confidence).

### Per language

- **Ukrainian (uk)** — "declining with high confidence (the data consistently shows this; still only a signal of reader interest): share fell 14.6%; 6,659 views/month."
- **Polish (pl)** — "declining with medium confidence (probably real, but weakened by the reasons listed): share fell 10.4%; 8,087 views/month; main reason: the share was lower than in the same month a year earlier in only 9 of 12 months."
- **German (de)** — "no clear change with medium confidence (probably real, but weakened by the reasons listed): share moved 0.7%, within the ±4% normal fluctuation; 23,477 views/month; main reason: 75% of all views in one period were detected bots, which are already excluded from these numbers; a share that high suggests some undetected bots may still be counted as users."
- **Spanish (es)** — "declining with low confidence (don't rely on this alone; check the reasons before acting): share fell 10.4%; 25,962 views/month; main reason: the change comes from a few unusual months; typical months show no clear change."
- **Portuguese (pt)** — "declining with low confidence (don't rely on this alone; check the reasons before acting): share fell 11.2%; 9,178 views/month; main reason: the change comes from a few unusual months; typical months show no clear change."
- **Turkish (tr)** — "no clear change with high confidence (the data consistently shows this; still only a signal of reader interest): share moved 0.2%, within the ±13% normal fluctuation; 7,080 views/month."
- **Japanese (ja)** — "declining with high confidence (the data consistently shows this; still only a signal of reader interest): share fell 11.0%; 36,383 views/month."
- **Vietnamese (vi)** — "no clear change with high confidence (the data consistently shows this; still only a signal of reader interest): share moved 1.6%, within the ±14% normal fluctuation; 12,478 views/month."

### Which to explore next

"Explore next: de and vi. de: Ranked 1 of 8 (score 0.80): momentum 1.00, stable: moved 0.7%, within the ±4% normal fluctuation; size 0.74, 23,477 views/month, the 3rd largest audience of 8; confidence 0.50, medium confidence (75% of all views in one period were detected bots, which are already excluded from these numbers; a share that high suggests some undetected bots may still be counted as users). vi: Ranked 2 of 8 (score 0.75): momentum 1.00, stable: moved 1.6%, within the ±14% normal fluctuation; size 0.37, 12,478 views/month, the 4th largest audience of 8; confidence 1.00, high confidence."

"Lower priority on this evidence: ja, tr, es, pl, uk, pt."

"Audiences here are the readers of each language's Wikipedia, not countries: one language is often read in many countries."

"Ranking weights: momentum 0.4, size 0.4, confidence 0.2; momentum and size are scaled 0-1 within these languages, so the score only compares them with each other."

### Scope

"Pageviews measure reader interest on Wikipedia, not willingness to pay or market size: use this to choose what to validate next, not to decide on its own."

### Files

- Chart: `<repo>/output/Q1860-english/chart.png`
- Report (PDF): `<repo>/output/Q1860-english/report.pdf`

---

**Bottom line for your question:** No audience shows growing interest in the English language article on Wikipedia. German (de) and Vietnamese (vi) rank highest for further exploration — both are stable (no clear change) with the largest audiences among the stable group, and vi carries high confidence. Japanese (ja) has the largest raw audience but is declining with high confidence. Ukrainian (uk) shows the steepest decline. Note that Spanish and Portuguese declines are low-confidence and driven by a few unusual months, so they may not reflect a real trend.
