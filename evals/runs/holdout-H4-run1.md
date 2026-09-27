# Run: holdout-H4-run1

**Prompt:** Чи зростає інтерес до вивчення англійської мови в українській Вікіпедії? Ми думаємо про курс англійської для українців.

**Model:** `claude-haiku-4-5-20251001`

**Tool call — Skill:**

```json
{
 "skill": "wikipedia-interest-trends",
 "args": "Ukrainian Wikipedia English language learning interest trends"
}
```

<details><summary>Tool result</summary>

```
Launching skill: wikipedia-interest-trends
```
</details>

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/setup.sh"
}
```

<details><summary>Tool result</summary>

```
setup: using uv (uv 0.12.18 (Homebrew 2026-09-22 aarch64-apple-darwin))
setup: OK - run the skill with exactly this command prefix:
<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py
```
</details>

**Tool call — Bash:**

```json
{
 "command": "<SKILL_DIR>/.venv/bin/python <SKILL_DIR>/scripts/wit.py compare \"English language\" --langs uk,pl,de,ru --months 24 --question \"Is interest in English growing in Ukrainian Wikipedia?\" --note \"Proxy: the Wikipedia article on the English language, read in each audience's own language. Usage patterns reflect reader interest in learning about or understanding the English language.\""
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
  "note": "Proxy: the Wikipedia article on the English language, read in each audience's own language. Usage patterns reflect reader interest in learning about or understanding the English language.",
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
     "q
… [5550 more chars]
```
</details>

### Assistant

**На жаль, дані показують протилежне:**

### Що було вимірено
Аналіз: статті про англійську мову (Англійська мова) в Вікіпедії за мовами. Період: останні 12 місяців (вересень 2025 – серпень 2026) порівняно з аналогічним періодом року раніше (вересень 2024 – серпень 2025).

### Основні висновки
- **Не зростає.** Натомість: **російська**, **українська** та **польська** — *скорочуються*; німецька — стабільна
- Частка уваги в українській Вікіпедії **впала на 14,6%** — скорочення з *високою впевненістю* (дані послідовні)
- Аудиторія англійської мови в українській Вікіпедії невелика: **6,659 переглядів/місяць** (для порівняння: російська — 86,788)

### Порівняння мов
За зміною частки уваги (від найбільшого скорочення):
- **Німецька** (де): без чітких змін, стабільно (+0,7%)
- **Польська** (pl): скорочення на 10,4%
- **Українська** (uk): скорочення на 14,6% ← **Ваш ринок**
- **Російська** (ru): скорочення на 41,6%

### Що це означає для вашого курсу
Дані Вікіпедії мають обмеження: вони показують *читацький інтерес на Вікіпедії*, не готовність платити за навчання. Скорочення може означати, що люди шукають інформацію про англійську в інших місцях, а не що попит на курси скорочується.

**Рекомендація:** Це дані для валідації гіпотези, а не остаточне рішення. Перевірте:
- Попит на платформах для навчання (Skillshare, Udemy, локальні курси)
- Соціальні медіа й пошукові запити про "англійська для українців"
- Прямі опитування вашої цільової аудиторії

📊 **Графік** розташований тут: `<repo>/output/Q1860-english/chart.png`

---

Turns: 5 · Duration: 28 s · Cost: $0.0374
