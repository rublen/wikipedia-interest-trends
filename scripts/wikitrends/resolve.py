"""Topic -> Wikidata item (QID) -> article title in each language edition."""

from __future__ import annotations

from wikitrends.api import Client

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_TTL = 24 * 3600  # items and sitelinks change; refresh daily
SITEMATRIX_API = "https://meta.wikimedia.org/w/api.php"
SITEMATRIX_TTL = 7 * 24 * 3600  # new Wikipedias are rare

SEARCH_LIMIT = 7
DESCRIPTION_CHARS = 90
# Auto-pick only if the top search hit is also the most-linked item and clearly dominant.
DOMINANCE_RATIO = 2.0


def site_for_lang(lang: str) -> str:
    """Wikipedia language code -> Wikidata site id: 'uk' -> 'ukwiki', 'zh-yue' -> 'zh_yuewiki'."""
    return lang.replace("-", "_") + "wiki"


def wikipedia_sites(client: Client) -> set[str]:
    """Site ids of all language Wikipedias (open and closed), from Wikimedia's site matrix.

    Sitelinks also point to sister projects whose ids look alike (e.g. 'abstractwiki',
    'commonswiki'), so an id pattern is not enough to tell which ones are Wikipedias.
    """
    data = client.get_json(SITEMATRIX_API, {
        "action": "sitematrix", "smtype": "language", "smlangprop": "code|site",
        "smsiteprop": "dbname|code", "smstate": "all", "format": "json", "formatversion": 2,
    }, ttl=SITEMATRIX_TTL)
    return {
        site["dbname"]
        for key, language in data["sitematrix"].items() if key != "count"
        for site in language.get("site", []) if site.get("code") == "wiki"
    }


def count_wikipedias(sitelinks: dict, wikipedias: set[str]) -> int:
    return sum(1 for site in sitelinks if site in wikipedias)


def search(client: Client, text: str, lang: str = "en") -> list[dict]:
    data = client.get_json(WIKIDATA_API, {
        "action": "wbsearchentities", "search": text, "language": lang, "uselang": lang,
        "type": "item", "limit": SEARCH_LIMIT, "format": "json",
    }, ttl=WIKIDATA_TTL)
    return [
        {"qid": hit["id"], "label": hit.get("label", ""), "description": hit.get("description", "")}
        for hit in data.get("search", [])
        # Disambiguation pages, categories, templates, list articles.
        if not hit.get("description", "").startswith("Wikimedia ")
    ]


def get_entities(client: Client, qids: list[str], lang: str = "en") -> dict[str, dict]:
    data = client.get_json(WIKIDATA_API, {
        "action": "wbgetentities", "ids": "|".join(qids), "props": "labels|descriptions|sitelinks",
        "languages": lang, "languagefallback": 1, "format": "json",
    }, ttl=WIKIDATA_TTL)
    entities = {}
    for qid, entity in data.get("entities", {}).items():
        if "missing" in entity:
            continue
        entities[qid] = {
            "qid": qid,
            "label": entity.get("labels", {}).get(lang, {}).get("value", ""),
            "description": entity.get("descriptions", {}).get(lang, {}).get("value", ""),
            "sitelinks": {site: link["title"] for site, link in entity.get("sitelinks", {}).items()},
        }
    return entities


def resolve(
    client: Client,
    langs: list[str],
    topic: str | None = None,
    qid: str | None = None,
    search_lang: str = "en",
) -> dict:
    """Return {"status": "resolved" | "ambiguous" | "not_found", ...}.

    resolved:  item, titles per language (None = no article), resolution
    ambiguous: resolution with the candidates to choose from (rerun with qid)
    `resolution` explains the decision: rule, best vs runner-up, all search candidates.
    """
    wikipedias = wikipedia_sites(client)

    if qid:
        entities = get_entities(client, [qid], search_lang)
        if qid not in entities:
            return {"status": "not_found", "message": f"Wikidata item {qid} does not exist"}
        resolution = {"method": "qid", "decision": "given_qid", "reason": f"chosen with --qid {qid}"}
        return _resolved(entities[qid], langs, wikipedias, resolution)

    hits = search(client, topic or "", search_lang)
    if not hits:
        return {
            "status": "not_found",
            "message": f"No Wikidata item matches {topic!r} (search language: {search_lang}). "
                       "Try another wording, the English name, or --search-lang.",
        }

    entities = get_entities(client, [h["qid"] for h in hits], search_lang)
    candidates = []
    for rank, hit in enumerate(hits, start=1):
        entity = entities.get(hit["qid"])
        if entity:
            description = entity["description"] or hit["description"]
            candidates.append({
                "search_rank": rank,
                "qid": hit["qid"],
                "label": entity["label"] or hit["label"],
                "description": (description if len(description) <= DESCRIPTION_CHARS
                                else description[:DESCRIPTION_CHARS - 1].rstrip() + "…"),
                "wikipedias": count_wikipedias(entity["sitelinks"], wikipedias),
            })

    decision, reason, best, runner_up, ratio = _decide(candidates)
    resolution = {
        "method": "search",
        "decision": decision,
        "reason": reason,
        "rule": f"auto-pick only if the first search result with Wikipedia articles is also the "
                f"item with the most articles, with at least {DOMINANCE_RATIO:g}x the runner-up",
        "best": _short(best),
        "runner_up": _short(runner_up) if runner_up else None,
        "ratio": ratio,
        "candidates": candidates,  # search order
    }
    if decision == "auto_picked":
        return _resolved(entities[best["qid"]], langs, wikipedias, resolution)
    return {
        "status": "ambiguous",
        "message": f"{topic!r} matches several Wikidata items. Pick the one the user means "
                   "(ask if unclear) and rerun with --qid.",
        "resolution": resolution,
    }


def _decide(candidates: list[dict]) -> tuple[str, str, dict, dict | None, float | None]:
    by_links = sorted(candidates, key=lambda c: c["wikipedias"], reverse=True)
    # Items without any Wikipedia article can't be analyzed, so they don't count as "#1".
    top = next((c for c in candidates if c["wikipedias"] > 0), candidates[0])
    best = by_links[0]
    runner_up = by_links[1] if len(by_links) > 1 else None
    runner_count = runner_up["wikipedias"] if runner_up else 0
    ratio = round(best["wikipedias"] / runner_count, 2) if runner_count else None
    ratio_text = f"{ratio:g}x" if ratio is not None else "no runner-up with articles"

    if best["wikipedias"] == 0:
        return "ambiguous", "no candidate has a Wikipedia article", best, runner_up, ratio
    if top is not best:
        return ("ambiguous",
                f"the first search result with articles ({top['qid']} {top['label']}, "
                f"{top['wikipedias']} Wikipedias) is not "
                f"the most-linked item ({best['qid']} {best['label']}, {best['wikipedias']})",
                best, runner_up, ratio)
    if ratio is not None and ratio < DOMINANCE_RATIO:
        return ("ambiguous",
                f"most-linked item has only {ratio_text} the Wikipedias of the runner-up "
                f"({runner_up['qid']} {runner_up['label']}); {DOMINANCE_RATIO:g}x required",
                best, runner_up, ratio)
    return ("auto_picked",
            f"the first search result with articles is also the most-linked item, with {ratio_text} "
            f"the Wikipedias of the "
            f"runner-up" + (f" ({runner_up['qid']} {runner_up['label']})" if runner_count else ""),
            best, runner_up, ratio)


def _short(candidate: dict) -> dict:
    return {k: candidate[k] for k in ("qid", "label", "wikipedias")}


def _resolved(entity: dict, langs: list[str], wikipedias: set[str], resolution: dict) -> dict:
    return {
        "status": "resolved",
        "item": {
            "qid": entity["qid"],
            "label": entity["label"],
            "description": entity["description"],
            "wikipedias": count_wikipedias(entity["sitelinks"], wikipedias),
        },
        "titles": {lang: entity["sitelinks"].get(site_for_lang(lang)) for lang in langs},
        "resolution": resolution,
    }
