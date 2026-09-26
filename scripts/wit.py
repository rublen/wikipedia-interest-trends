#!/usr/bin/env python3
"""wit: Wikipedia interest trends CLI (entry point for the agent skill).

Every command prints one JSON object to stdout. Exit codes: 0 = a JSON answer was
produced (check its "status"), 1 = API/network or spec error, 2 = invalid arguments.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from wikitrends import __version__, pipeline
from wikitrends.api import ApiError, Client
from wikitrends.resolve import resolve

# Country codes often used by mistake for Wikipedia language codes (none of these is a Wikipedia).
LANG_HINTS = {"ua": "uk", "cz": "cs", "gr": "el", "jp": "ja", "dk": "da"}
LANG_CODE = re.compile(r"^[a-z]{2,3}(-[a-z]{2,8})*$")


def today() -> date:
    return datetime.now(timezone.utc).date()


def emit(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=1))


def parse_langs(value: str) -> list[str]:
    langs = []
    for raw in value.split(","):
        lang = raw.strip().lower()
        if not lang:
            continue
        if lang in LANG_HINTS:
            raise argparse.ArgumentTypeError(
                f"'{lang}' is a country code, not a Wikipedia language code; did you mean '{LANG_HINTS[lang]}'?")
        if not LANG_CODE.match(lang):
            raise argparse.ArgumentTypeError(f"invalid language code '{lang}' (examples: en, uk, pl, zh-yue)")
        if lang not in langs:
            langs.append(lang)
    if not langs:
        raise argparse.ArgumentTypeError("give at least one language code, e.g. --langs pl,cs")
    return langs


def parse_months(value: str) -> int:
    try:
        months = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--months must be an integer") from None
    if months < 1:
        raise argparse.ArgumentTypeError("--months must be at least 1")
    return months


def _resolve_and_spec(args: argparse.Namespace, client: Client) -> tuple[dict, dict | None]:
    if not args.topic and not args.qid:
        raise argparse.ArgumentTypeError("give a topic or --qid")
    resolved = resolve(client, args.langs, topic=args.topic, qid=args.qid, search_lang=args.search_lang)
    if resolved["status"] != "resolved":
        return resolved, None
    spec = pipeline.build_spec(client, resolved, args.topic, args.langs, args.months, today())
    return resolved, spec


def cmd_compare(args: argparse.Namespace, client: Client) -> int:
    resolved, spec = _resolve_and_spec(args, client)
    if spec is None:
        emit(resolved)
        return 0
    out_dir = Path(args.out) if args.out else pipeline.default_out_dir(spec)
    spec_path = out_dir / "query.json"
    pipeline.write_json(spec_path, spec)
    result = pipeline.analyze_spec(client, spec, out_dir)
    result["topic"]["resolution"] = resolved["resolution"]
    result["files"]["spec"] = str(spec_path)
    emit(result)
    return 0


def cmd_resolve(args: argparse.Namespace, client: Client) -> int:
    resolved, spec = _resolve_and_spec(args, client)
    if spec is not None:
        out_dir = Path(args.out) if args.out else pipeline.default_out_dir(spec)
        spec_path = out_dir / "query.json"
        pipeline.write_json(spec_path, spec)
        resolved["period"] = {"start": spec["start"], "end": spec["end"], "notes": spec["notes"]}
        resolved["spec"] = str(spec_path)
    emit(resolved)
    return 0


def cmd_fetch(args: argparse.Namespace, client: Client) -> int:
    spec = pipeline.load_spec(args.spec)
    data = pipeline.fetch(client, spec)
    emit({
        "status": "ok",
        "period": f"{spec['start']}..{spec['end']}",
        "languages": {
            lang: {
                "article_views_total": sum(d["article"].values()) if d["article"] is not None else None,
                "project_views_total": sum(d["project"].values()),
            }
            for lang, d in data.items()
        },
        "network_requests": client.network_requests,
    })
    return 0


def cmd_analyze(args: argparse.Namespace, client: Client) -> int:
    spec_path = Path(args.spec)
    spec = pipeline.load_spec(spec_path)
    out_dir = Path(args.out) if args.out else spec_path.parent
    result = pipeline.analyze_spec(client, spec, out_dir)
    result["files"]["spec"] = str(spec_path)
    emit(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wit.py",
        description="Analyze Wikipedia pageview trends across topics and language editions. "
                    "Every command prints one JSON object.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add_query_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("topic", nargs="?", help='topic to look up, e.g. "intermittent fasting"')
        p.add_argument("--qid", help="Wikidata item id (e.g. Q1666254); use after an 'ambiguous' answer")
        p.add_argument("--langs", required=True, type=parse_langs,
                       help="comma-separated Wikipedia language codes, e.g. pl,cs,uk")
        p.add_argument("--months", type=parse_months, default=24,
                       help="last N complete months, compared with the same months a year earlier; "
                            "above 12, the comparison is the last 12 months and the rest only extends "
                            "the chart (default 24)")
        p.add_argument("--search-lang", default="en", help="language the topic is written in (default en)")
        p.add_argument("--out", help="output directory (default: output/<qid>-<label>/)")

    p = sub.add_parser("compare", help="Resolve a topic, fetch pageviews, analyze and chart (primary command)")
    add_query_args(p)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("resolve", help="Find the Wikidata item and article titles; write a query spec")
    add_query_args(p)
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("fetch", help="Download monthly pageviews for a query spec (cached)")
    p.add_argument("--spec", required=True, help="path to query.json written by resolve")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("analyze", help="Compute growth and normalized share for a query spec; draw the chart")
    p.add_argument("--spec", required=True, help="path to query.json written by resolve")
    p.add_argument("--out", help="output directory (default: the spec's directory)")
    p.set_defaults(func=cmd_analyze)

    return parser


def main(argv: list[str] | None = None, client: Client | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        return args.func(args, client or Client())
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    except (ApiError, pipeline.SpecError, OSError, json.JSONDecodeError) as exc:
        emit({"status": "error", "message": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
