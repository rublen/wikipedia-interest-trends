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
