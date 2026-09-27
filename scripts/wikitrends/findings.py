"""Key findings: short, standalone sentences with every cross-language comparison precomputed.

Agents quote short sentences and paraphrase long text, and cross-language claims they worked
out themselves ("Turkish is the smallest", "all six others are declining") were their most
common critical error. So every such claim is computed here, and each sentence can be quoted
on its own. Empty categories are stated ("Growing: none") rather than left out.
"""

from __future__ import annotations

GROUPS = [("growing", "Growing"), ("no_clear_change", "Stable (no clear change)"), ("declining", "Declining")]


def _names(langs: list[str]) -> str:
    if not langs:
        return "none"
    return langs[0] if len(langs) == 1 else ", ".join(langs[:-1]) + " and " + langs[-1]


def _extreme(ok: dict[str, dict], order: list[str], key, best: bool) -> list[str]:
    """Languages sharing the highest (best=True) or lowest value of `key`, in `order`."""
    values = {lang: key(ok[lang]) for lang in order}
    target = max(values.values()) if best else min(values.values())
    return [lang for lang in order if values[lang] == target]


def key_findings(topic: dict, languages: dict[str, dict], ranking: dict, note: str | None) -> list[str]:
    findings = [f"Analyzing: “{topic['label']}” ({topic['qid']}), {topic['description']}."
                + (f" {note}" if note else "")]

    ranked = [row["lang"] for row in ranking["languages"]]
    ok = {lang: languages[lang] for lang in ranked}
    if not ok:
        findings.append("No language could be measured: none has an article with comparable data.")
        return findings

    # 1. Which languages are growing / stable / declining (every category stated).
    findings.append(" ".join(
        f"{label}: {_names([lang for lang in ranked if ok[lang]['trend']['verdict'] == verdict])}."
        for verdict, label in GROUPS))

    # 2. Audience size extremes.
    if len(ok) == 1:
        lang = ranked[0]
        findings.append(f"Only one language could be measured: {lang} "
                        f"({ok[lang]['avg_monthly_views_recent']:,} views/month).")
    else:
        def views(r):
            return r["avg_monthly_views_recent"]
        largest = _extreme(ok, ranked, views, best=True)
        smallest = _extreme(ok, ranked, views, best=False)
        each = lambda group: " each" if len(group) > 1 else ""  # noqa: E731
        findings.append(f"Largest audience: {_names(largest)} ({views(ok[largest[0]]):,} views/month"
                        f"{each(largest)}); smallest: {_names(smallest)} ({views(ok[smallest[0]]):,} "
                        f"views/month{each(smallest)}).")

    # 3. Strongest confirmed growth and steepest confirmed decline in share.
    parts = []
    for verdict, label, best, verb in [("growing", "Strongest growth in share", True, "rose"),
                                       ("declining", "Steepest decline in share", False, "fell")]:
        members = {lang: r for lang, r in ok.items() if r["trend"]["verdict"] == verdict}
        if not members:
            parts.append(f"{label}: none.")
            continue
        order = [lang for lang in ranked if lang in members]
        top = _extreme(members, order, lambda r: round(r["share_growth_pct"], 1), best=best)
        pct = abs(members[top[0]]["share_growth_pct"])
        parts.append(f"{label}: {_names(top)} ({verb} {pct:.1f}%{' each' if len(top) > 1 else ''}).")
    findings.append(" ".join(parts))

    # 4. Ranking (only when there is something to rank).
    if len(ranked) > 1:
        w = ranking["weights"]
        findings.append(f"Ranked first: {ranked[0]}, then {ranked[1]} (weights: momentum {w['momentum']:g}, "
                        f"size {w['size']:g}, confidence {w['confidence']:g}).")

    # 5. Results not to rely on alone, and languages that couldn't be measured.
    low = [lang for lang in ranked if ok[lang]["trend"]["confidence"] == "low"]
    findings.append(f"Low confidence, don't rely on these alone: {_names(low)}.")
    if ranking["not_ranked"]:
        findings.append(f"Not measurable (no article or no comparable data): {_names(list(ranking['not_ranked']))}.")
    return findings
