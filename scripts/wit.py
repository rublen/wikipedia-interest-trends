#!/usr/bin/env python3
"""wit: Wikipedia interest trends CLI (entry point for the agent skill)."""

from __future__ import annotations

import argparse
import json
import sys

from wikitrends import __version__


def cmd_not_implemented(args: argparse.Namespace) -> int:
    print(json.dumps({"error": f"'{args.command}' is not implemented yet"}))
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wit.py",
        description="Analyze Wikipedia pageview trends across topics and language editions.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    planned = {
        "compare": "Resolve a topic, fetch pageviews, analyze and chart (primary command)",
        "resolve": "Find a topic's Wikidata item and article titles per language",
        "fetch": "Download monthly pageviews for a query spec",
        "analyze": "Compute growth and normalized share for a query spec",
    }
    for name, help_text in planned.items():
        p = sub.add_parser(name, help=f"{help_text} [not implemented yet]")
        p.set_defaults(func=cmd_not_implemented)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
