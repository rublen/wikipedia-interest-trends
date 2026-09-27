"""Query spec, fetching and analysis, shared by the `compare`, `resolve`, `fetch` and `analyze` commands."""

from __future__ import annotations

import copy
import csv
import json
import re
from datetime import date
from pathlib import Path

from wikitrends import analyze, chart, findings, ranking, report, trust
from wikitrends.api import Client
from wikitrends.config import OUTPUT_DIR
from wikitrends.months import FIRST_AVAILABLE, add_months, last_complete_month, month_range
from wikitrends.pageviews import article_monthly, project_monthly
from wikitrends.resolve import language_names

SPEC_VERSION = 2  # 2: year-on-year comparison window

# Quoted once per answer (SKILL.md): keeps the conclusion within what pageviews can show.
SCOPE = ("Pageviews measure reader interest on Wikipedia, not willingness to pay or market size: "
         "use this to choose what to validate next, not to decide on its own.")

# (The "interest is not willingness to pay" limitation is the `scope` sentence above; a second,
# similar wording here made agents quote one or the other.)
LIMITATIONS = [
    "One Wikidata item = one article per language; related articles and redirects are not counted.",
    "agent=user excludes identified bots, but undetected bots can remain (classification improved in April 2020).",
    "Confidence comes from rules of thumb (volume, spikes, consistency, noise, data artifacts), not a statistical model.",
]
# Files analyze_spec writes; removed at the start of each run so none can be left over
# from an earlier run with different languages (query.json is written by the caller).
GENERATED_FILES = ("chart.png", "monthly.csv", "result.json", "report.pdf")



class SpecError(ValueError):
    """The requested period or spec is invalid."""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "topic"


def build_spec(client: Client, resolved: dict, query: str | None, langs: list[str], months: int,
               today: date) -> dict:
    notes = []
    end = last_complete_month(today)
    # Monthly data for the last month is published a few days after it ends.
    check_lang = next((lang for lang in langs if resolved["titles"].get(lang)), "en")
    if project_monthly(client, check_lang, end, end, last_complete=end)[end] == 0:
        notes.append(f"{end} is not published yet; the period ends at {add_months(end, -1)}")
        end = add_months(end, -1)
    # Compare the last `window` months with the same months a year earlier; a longer
    # `months` only extends the history shown in the chart and used by the trust checks.
    window = min(months, trust.YEAR)
    total = max(months, window + trust.YEAR)
    start = add_months(end, -(total - 1))
    if start < FIRST_AVAILABLE:
        available = len(month_range(FIRST_AVAILABLE, end))
        raise SpecError(f"pageview data starts at {FIRST_AVAILABLE}; at most {available} "
                        f"months are available up to {end}")

    item = resolved["item"]
    return {
        "spec_version": SPEC_VERSION,
        "query": query,
        "qid": item["qid"],
        "label": item["label"],
        "description": item["description"],
        "langs": langs,
        "titles": resolved["titles"],
        "months": months,
        "window": window,
        "start": start,
        "end": end,
        "last_complete_month": last_complete_month(today),
        "notes": notes,
    }


def default_out_dir(spec: dict) -> Path:
    return OUTPUT_DIR / f"{spec['qid']}-{slugify(spec['label'] or spec['query'] or '')}"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_spec(path: Path) -> dict:
    spec = json.loads(Path(path).read_text())
    if spec.get("spec_version") != SPEC_VERSION:
        raise SpecError(f"{path}: unsupported spec_version {spec.get('spec_version')!r}")
    return spec


def fetch(client: Client, spec: dict) -> dict[str, dict]:
    """{lang: {"article": {month: views} | None, "project": {month: views}}} for the spec's period."""
    start, end, last = spec["start"], spec["end"], spec["last_complete_month"]
    data = {}
    for lang in spec["langs"]:
        title = spec["titles"].get(lang)
        data[lang] = {
            "article": article_monthly(client, lang, title, start, end, last) if title else None,
            "automated": article_monthly(client, lang, title, start, end, last, agent="automated")
                         if title else None,
            "project": project_monthly(client, lang, start, end, last),
        }
    return data


def reproduce_command(spec: dict, weights: dict[str, float]) -> str:
    cmd = f"wit.py compare --qid {spec['qid']} --langs {','.join(spec['langs'])} --months {spec['months']}"
    if weights != ranking.parse_weights(None):
        cmd += " --weights " + ",".join(f"{k}={v:g}" for k, v in weights.items())
    return cmd + " --report"


# More measurable languages than this: stdout gets the compact form (see `compact`).
COMPACT_ABOVE = 2


def analyze_spec(client: Client, spec: dict, out_dir: Path, weights: dict[str, float] | None = None,
                 make_report: bool = False, question: str | None = None, note: str | None = None,
                 details: bool = False) -> dict:
    """Returns the agent-facing result: compact for many languages unless `details`.

    result.json always gets the full agent-facing version.
    """
    months = month_range(spec["start"], spec["end"])
    window = spec["window"]
    previous, recent = trust.windows(months, window)
    data = fetch(client, spec)
    out_dir = Path(out_dir)
    for name in GENERATED_FILES:
        (out_dir / name).unlink(missing_ok=True)

    languages, plotted, not_shown = {}, {}, {}
    for lang in spec["langs"]:
        article, project = data[lang]["article"], data[lang]["project"]
        if not any(project.values()):
            languages[lang] = {"status": "unknown_language",
                               "note": f"no {lang}.wikipedia project data; check the language code"}
            not_shown[lang] = "unknown language code"
        elif article is None:
            languages[lang] = {"status": "no_article",
                               "note": f"no {lang} Wikipedia article is linked to {spec['qid']}; "
                                       "interest can't be measured there with this method"}
            not_shown[lang] = "no article on this topic"
        else:
            languages[lang] = {"status": "ok", "title": spec["titles"][lang],
                               **analyze.analyze_language(months, article, project, lang,
                                                          data[lang]["automated"], window)}
            plotted[lang] = {"views": article, "share": analyze.monthly_share(article, project)}

    ranked = sorted((lang for lang, r in languages.items() if r.get("share_growth_pct") is not None),
                    key=lambda lang: languages[lang]["share_growth_pct"], reverse=True)

    result = {
        "status": "ok",
        "topic": {"query": spec["query"], "qid": spec["qid"], "label": spec["label"],
                  "description": spec["description"], "note": note},
        "key_findings": [],
        "period": {"comparison": f"last {window} complete month{'s' if window > 1 else ''} vs the "
                                 "same months a year earlier",
                   "recent": f"{recent[0]}..{recent[-1]}", "previous": f"{previous[0]}..{previous[-1]}",
                   "chart": f"{months[0]}..{months[-1]}", "notes": spec["notes"]},
        "languages": languages,
        "ranking_by_share_growth": ranked,
        "comparison": analyze.comparison(languages),
        "ranking": ranking.rank(languages, weights or ranking.parse_weights(None)),
        "recommendation": [],
        "scope": SCOPE,
        "files": {},
        "limitations": LIMITATIONS,
    }

    if plotted:
        chart_path = out_dir / "chart.png"
        drawn = chart.render(
            chart_path,
            title=f"Interest in “{spec['label']}” ({spec['qid']}) on Wikipedia",
            months=months,
            series=plotted,
            footnote=f"Source: Wikimedia Pageviews API, monthly, agent=user. Compared: "
                     f"{result['period']['recent']} vs {result['period']['previous']} (same months a year earlier).",
            compared=(previous, recent),
            order=spec["langs"],
            not_shown=not_shown,
        )
        result["files"]["chart"] = str(chart_path)
        skipped = [lang for lang in plotted if lang not in drawn]
        if skipped:
            result["period"]["notes"].append(f"chart shows {len(drawn)} languages; "
                                             f"not drawn: {', '.join(skipped)}")
    else:
        result["period"]["notes"].append("no chart: none of the languages has an article to plot")

    result["recommendation"] = ranking.recommendation(result["ranking"])
    result["key_findings"] = findings.key_findings(result["topic"], languages, result["ranking"], note)
    if make_report:
        report_path = out_dir / "report.pdf"
        fits = report.render(report_path, result, months, plotted, (previous, recent), spec["langs"],
                             language_names(client), question, note,
                             reproduce_command(spec, result["ranking"]["weights"]))
        result["files"]["report"] = str(report_path)
        if not fits:
            result["period"]["notes"].append("report: not everything fit on one page; "
                                             "compare fewer languages for a complete report")

    csv_path = out_dir / "monthly.csv"
    _write_csv(csv_path, months, data)
    result["files"]["data"] = str(csv_path)
    result_path = out_dir / "result.json"
    result["files"]["result"] = str(result_path)
    full = model_facing(result)
    write_json(result_path, full)
    measurable = sum(1 for r in result["languages"].values() if r.get("share_growth_pct") is not None)
    return full if details or measurable <= COMPACT_ABOVE else compact(result, full)


def _line(r: dict) -> str:
    """One code-written line per language for the compact output."""
    trend = r["trend"]
    verdict = trend["verdict"].replace("_", " ")
    text = (f"{verdict} with {trend['confidence']} confidence ({trust.MEANINGS[trend['confidence']]}): "
            f"share {analyze.share_change_text(r['share_growth_pct'], trend)}; "
            f"{r['avg_monthly_views_recent']:,} views/month")
    if trend["confidence"] != "high" and trend["reasons"]:
        text += f"; main reason: {trend['reasons'][0]}"
    return text + "."


def compact(result: dict, full: dict) -> dict:
    """Agent-facing result for many languages: findings, comparison and one line per language.

    Full per-language summaries made the answer long, and agents then paraphrased and wrote
    their own cross-language claims instead of quoting `key_findings`; leaving them out of the
    default output removes that competing text.
    """
    out = {k: v for k, v in full.items() if k not in ("languages", "ranking", "ranking_by_share_growth")}
    out["languages"] = {}
    for lang, r in result["languages"].items():
        if r.get("status") == "ok" and r.get("share_growth_pct") is not None:
            out["languages"][lang] = {"status": "ok", "title": r["title"], "line": _line(r)}
        else:
            out["languages"][lang] = full["languages"][lang]
    out["ranking"] = {
        "weights": full["ranking"]["weights"],
        "languages": [{k: row[k] for k in ("lang", "rank", "score")} for row in full["ranking"]["languages"]],
        "not_ranked": full["ranking"]["not_ranked"],
    }
    out["details"] = ("Compact output for many languages. Per-language summaries and all reasons: "
                      "files.result, the PDF report, or rerun with --details.")
    # Keep the reading order: findings and comparison before the per-language lines.
    order = ["status", "topic", "key_findings", "period", "comparison", "languages", "recommendation",
             "ranking", "scope", "files", "limitations", "details"]
    return {k: out[k] for k in order if k in out}


def model_facing(result: dict) -> dict:
    """The result as agents see it (stdout, result.json): changes in words, no signed numbers.

    Human-facing outputs (the CSV and the PDF table) keep the signed numbers. Agents read
    words instead: a sign is easy to misread, and the direction of a noise-level change is
    easy to over-read ("rose 1.6%" became "growing" in agent answers), so a "no clear change"
    is described by its size relative to the noise, without a direction.
    """
    out = copy.deepcopy(result)
    for r in out["languages"].values():
        if r.get("status") != "ok":
            continue
        trend = r["trend"]
        share, views, project = (r.pop("share_growth_pct"), r.pop("views_growth_pct"),
                                 r.pop("project_growth_pct"))
        r["share_change"] = analyze.share_change_text(share, trend) if share is not None else None
        r["views_change"] = analyze.change_text(views) if views is not None else None
        r["project_change"] = analyze.change_text(project, "grew", "shrank") if project is not None else None
        median = trend["checks"].pop("median_share_growth_pct", None)
        if median is not None and trend["verdict"] in ("growing", "declining"):
            trend["checks"]["median_share_change"] = analyze.change_text(median)
    for row in out["ranking"]["languages"]:
        row.pop("share_growth_pct", None)
    return out


def _write_csv(path: Path, months: list[str], data: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "lang", "article_views", "project_views", "share_per_million"])
        for lang, series in data.items():
            for month in months:
                article = series["article"][month] if series["article"] is not None else ""
                project = series["project"][month]
                share = analyze.share_per_million(article, project) if article != "" else None
                writer.writerow([month, lang, article, project, "" if share is None else f"{share:.4f}"])
