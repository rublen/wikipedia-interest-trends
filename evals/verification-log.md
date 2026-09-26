# Verification log

Numbers produced by the skill, checked against an independent source. Each entry:
what was checked, how, expected vs observed, verdict.

## 1. Czech "Přerušovaný půst" (intermittent fasting), user views — 2026-09-25

Command: `.venv/bin/python scripts/wit.py compare "intermittent fasting" --langs pl,cs --months 24`

| Value | Skill output | Independent (manual) check | Match? |
|---|---|---|---|
| Article views, 2024-09..2025-08 | 4,741 | 4,741 | yes |
| Article views, 2025-09..2026-08 | 2,198 | 2,198 | yes |
| cs.wikipedia total views, 2024-09..2025-08 | 816,011,502 (sum of `monthly.csv`) | 815,921,445 | within 0.011%, explained below |
| Polish article exists? | no (`no_article`) | no | yes |

How to check by hand (browser, no code from this repo):
- Article views: [pageviews.wmcloud.org, previous window](https://pageviews.wmcloud.org/?project=cs.wikipedia.org&platform=all-access&agent=user&redirects=0&start=2024-09-01&end=2025-08-31&pages=P%C5%99eru%C5%A1ovan%C3%BD_p%C5%AFst)
  and [recent window](https://pageviews.wmcloud.org/?project=cs.wikipedia.org&platform=all-access&agent=user&redirects=0&start=2025-09-01&end=2026-08-31&pages=P%C5%99eru%C5%A1ovan%C3%BD_p%C5%AFst).
  Check that platform = all-access, agent = user, and redirects are off; compare the total "Pageviews".
- Project total: [siteviews, cs.wikipedia](https://pageviews.wmcloud.org/siteviews/?platform=all-access&source=pageviews&agent=user&start=2024-09-01&end=2025-08-31&sites=cs.wikipedia.org).
- Polish article: [Wikidata Q1666254](https://www.wikidata.org/wiki/Q1666254), "Wikipedia" sitelinks list: no `plwiki`.

**Finding: monthly vs daily data differ slightly.** The 90,057-view gap in the project total
is all in one month: the API's *monthly* aggregate for cs.wikipedia, March 2025, is
74,887,886, while its *daily* values for that month sum to 74,797,829. All other months
match exactly. The skill uses monthly data; pageviews.wmcloud.org sums daily data. Impact
on conclusions: none at this size (0.011%), but hand checks should expect small gaps like this.

Also cross-checked (same API, different code): a standalone script written before the
CLI existed computed the same values (−53.6% raw, −47.0% share, −12.6% project) for cs.

## 2. Wikipedia counts used by the auto-pick rule — 2026-09-26

Command: `.venv/bin/python scripts/wit.py resolve astronomy --langs uk` (`resolution` block).

| Value | Skill output (before fix) | Independent (manual) check | Match? |
|---|---|---|---|
| Wikipedias with an article on Q333 (astronomy) | 253 | 252 ("Wikipedia (252 entries)" on [Q333](https://www.wikidata.org/wiki/Q333)) | **no, off by 1** |
| Wikipedias with an article on Q411 (astrobiology) | 92 | 92 ([Q411](https://www.wikidata.org/wiki/Q411)) | yes |

**Bug found:** the skill counted a sitelink as a Wikipedia if its id looked like
`<letters>wiki` minus a hand-made exclusion list. Q333 also links to `abstractwiki`
(Abstract Wikipedia, a newer Wikimedia project), which matched the pattern. Same for Q308
(planet Mercury): 251 instead of 250.

**Fix:** count only sites listed as Wikipedias in Wikimedia's official site matrix
(`action=sitematrix`, cached 7 days) instead of guessing from the id. After the fix: Q333
= 252, Q411 = 92, Q308 = 250. The astronomy ratio changed from 2.75 to 2.74; no decision
changed. Regression test: `test_sister_projects_are_not_counted_as_wikipedias`.

## 3. Ukrainian "Астрономія" (astronomy): "10 of 12 months below the same month a year earlier" — 2026-09-27

Command: `.venv/bin/python scripts/wit.py compare --qid Q333 --langs uk` (the example #2 scenario).
The count is on the **share** (article views ÷ all uk.wikipedia views, per million), so each
month needs two numbers. Values the skill used (`output/Q333-astronomy/monthly.csv`):

| Month | Article, year earlier | uk.wikipedia, year earlier | Share | Article, recent | uk.wikipedia, recent | Share | Recent vs year earlier |
|---|---|---|---|---|---|---|---|
| Sep | 4,687 | 74,509,285 | 62.90 | 1,642 | 61,256,706 | 26.81 | lower |
| Oct | 1,776 | 83,014,264 | 21.39 | 635 | 66,044,662 | 9.61 | lower |
| Nov | 1,746 | 83,835,060 | 20.83 | 557 | 67,137,685 | 8.30 | lower |
| Dec | 1,634 | 84,431,475 | 19.35 | 622 | 55,497,356 | 11.21 | lower |
| Jan | 1,558 | 94,111,809 | 16.55 | 449 | 60,471,976 | 7.42 | lower |
| Feb | 1,296 | 81,951,788 | 15.81 | 425 | 51,614,348 | 8.23 | lower |
| Mar | 1,068 | 79,609,260 | 13.42 | 410 | 55,114,806 | 7.44 | lower |
| Apr | 1,019 | 72,146,878 | 14.12 | 405 | 53,385,280 | 7.59 | lower |
| May | 789 | 69,040,303 | 11.43 | 600 | 55,950,057 | 10.72 | lower |
| Jun | 361 | 53,652,676 | 6.73 | 281 | 48,312,008 | 5.82 | lower |
| Jul | 305 | 62,209,478 | 4.90 | 322 | 52,999,047 | 6.08 | higher |
| Aug | 375 | 61,801,817 | 6.07 | 360 | 50,720,483 | 7.10 | higher |

Year earlier = Sep 2024 – Aug 2025; recent = Sep 2025 – Aug 2026. 10 lower, 2 higher.

Manual check (browser; switch the tools to **monthly** and use agent = user, all-access):

| Month pair | Value | Skill | Independent (manual) check | Match? |
|---|---|---|---|---|
| Sep 2024 / Sep 2025 | article views | 4,687 / 1,642 | 4,687 / 1,642 | yes |
| Sep 2024 / Sep 2025 | uk.wikipedia views | 74,509,285 / 61,256,706 | 74,509,285 / 61,256,706 | yes |
| Jan 2025 / Jan 2026 | article views | 1,558 / 449 | 1,558 / 449 | yes |
| Jan 2025 / Jan 2026 | uk.wikipedia views | 94,111,809 / 60,471,976 | 94,111,809 / 60,471,976 | yes |
| Jul 2025 / Jul 2026 | article views | 305 / 322 | 305 / 322 | yes |
| Jul 2025 / Jul 2026 | uk.wikipedia views | 62,209,478 / 52,999,047 | 62,209,478 / 52,999,047 | yes |

- Article: [pageviews.wmcloud.org, Астрономія](https://pageviews.wmcloud.org/?project=uk.wikipedia.org&platform=all-access&agent=user&redirects=0&start=2024-09-01&end=2026-08-31&pages=%D0%90%D1%81%D1%82%D1%80%D0%BE%D0%BD%D0%BE%D0%BC%D1%96%D1%8F)
- Whole Ukrainian Wikipedia: [siteviews, uk.wikipedia](https://pageviews.wmcloud.org/siteviews/?platform=all-access&source=pageviews&agent=user&start=2024-09-01&end=2026-08-31&sites=uk.wikipedia.org)
- Then recompute the share for each checked pair (article ÷ total × 1,000,000) and confirm
  its direction. As entry 1 showed, monthly totals can differ slightly from summed daily
  values; small gaps are expected, a different direction is not.

**Result:** all six values match exactly. Recomputed shares: Sep 62.90 → 26.81 (lower),
Jan 16.55 → 7.42 (lower), Jul 4.90 → 6.08 (higher), the same directions as the skill.
