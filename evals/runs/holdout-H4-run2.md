# Run: holdout-H4-run2

**Prompt:** Чи зростає інтерес до вивчення англійської мови в українській Вікіпедії? Ми думаємо про курс англійської для українців.

**Model:** `claude-haiku-4-5-20251001`

**Tool call — Skill:**

```json
{
 "skill": "wikipedia-interest-trends",
 "args": "topic:English language learners trend:Ukrainian Wikipedia language:uk"
}
```

<details><summary>Tool result</summary>

```
Launching skill: wikipedia-interest-trends
```
</details>

### Assistant

Аналізую, зростає чи інтерес до англійської мови в українській Вікіпедії. Почну з налаштування скрипту.

**Tool call — Bash:**

```json
{
 "command": "/private/tmp/claude-501/-Users-mymac-home-wikipedia-interest-trends/7afeb3de-e8ff-408d-b5fe-50376521d72b/scratchpad/sandbox/.claude/skills/wikipedia-interest-trends/setup.sh",
 "description": "Set up the Wikipedia interest trends skill"
}
```

<details><summary>Tool result</summary>

```
setup: using uv (uv 0.12.18 (Homebrew 2026-09-22 aarch64-apple-darwin))
setup: OK - run the skill with exactly this command prefix:
/private/tmp/claude-501/-Users-mymac-home-wikipedia-interest-trends/7afeb3de-e8ff-408d-b5fe-50376521d72b/scratchpad/sandbox/.claude/skills/wikipedia-interest-trends/.venv/bin/python /private/tmp/claude-501/-Users-mymac-home-wikipedia-interest-trends/7afeb3de-e8ff-408d-b5fe-50376521d72b/scratchpad/sandbox/.claude/skills/wikipedia-interest-trends/scripts/wit.py
```
</details>

**Tool call — Bash:**

```json
{
 "command": "/private/tmp/claude-501/-Users-mymac-home-wikipedia-interest-trends/7afeb3de-e8ff-408d-b5fe-50376521d72b/scratchpad/sandbox/.claude/skills/wikipedia-interest-trends/.venv/bin/python /private/tmp/claude-501/-Users-mymac-home-wikipedia-interest-trends/7afeb3de-e8ff-408d-b5fe-50376521d72b/scratchpad/sandbox/.claude/skills/wikipedia-interest-trends/scripts/wit.py compare \"English language\" --langs uk --months 24 --note \"Proxy: article on the English language, read on Ukrainian Wikipedia.\"",
 "description": "Analyze English language interest trends on Ukrainian Wikipedia"
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
  "note": "Proxy: article on the English language, read on Ukrainian Wikipedia.",
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
     "description": "literary works written in the English
… [4674 more chars]
```
</details>

### Assistant

На жаль, **інтерес до вивчення англійської на українській Вікіпедії спадає**, а не зростає.

**Що вимірювалось:**
Аналізувався артикул про англійську мову на українській Вікіпедії, порівнюючи останні 12 місяців (вересень 2025 — серпень 2026) з тим же періодом року раніше (вересень 2024 — серпень 2025).

**Ключові знахідки:**
- **Спадання**: українська мова (uk) — спад з висока впевненістю
- Кількість переглядів артикулу впала з 124,117 до 79,903 за 12 порівнюваних місяців (спад на 35,6%)
- Навіть з урахуванням того, що вся українська Вікіпедія скоротилась на 24,6%, артикул англійської втратив позиції: його частка всіх переглядів впала на 14,6%
- Це **послідовний спад** — частка була нижчою, ніж рік раніше, у всіх 12 місяцях

**Висновок:**
Якщо планується курс англійської для українців, не варто опиратись на трендах Вікіпедії як на сигнал попиту. Швидше за все, потрібні інші дані про факторів інтересу (соціальні мережі, пошукові запити, розповсюджувачі контенту).

Графік з даними: `/Users/mymac/home/wikipedia-interest-trends/output/Q1860-english/chart.png`

---

Turns: 5 · Duration: 25 s · Cost: $0.0281
