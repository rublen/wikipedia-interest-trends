#!/usr/bin/env python3
"""Run agent scenarios headless and save their transcripts (the step that produced evals/runs/).

Each run gets a fresh sandbox folder with the skill installed as
`.claude/skills/wikipedia-interest-trends` (a link to this repository), and runs
`claude -p` with project settings only (no personal settings or memory) and an allowlist
limited to the skill: `Skill`, `Read`, `<SKILL_DIR>/setup.sh` and `<SKILL_DIR>/.venv/bin/python
<SKILL_DIR>/scripts/wit.py`. Multi-turn scenarios continue the same conversation (`--continue`).

For every run it writes `<out>/<prefix>-<scenario>-run<N>[-turn<k>].jsonl` (raw log, gitignored:
contains session metadata) and a Markdown transcript without metadata or local paths, then
prints turns, cost, tool errors and the grounding check. Scoring against rubric.md is done by
reading the transcripts; this script only produces them.

Examples:
    uv run --locked python evals/run_scenarios.py --list
    uv run --locked python evals/run_scenarios.py H1 H3 --runs 2
    uv run --locked python evals/run_scenarios.py --set holdout --runs 2 --prefix holdout-v2
    uv run --locked python evals/run_scenarios.py ex3 --dry-run

Needs the Claude Code CLI (`claude`) on PATH; the scripts in evals/ use only the Python
standard library. Costs money on paid models (a Haiku run is about $0.02-0.06). For OpenRouter, set
ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN in the environment and pass `--model <openrouter id>`.
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
sys.path.insert(0, str(EVALS))

import grounding  # noqa: E402
import transcript  # noqa: E402

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
SKILL_NAME = "wikipedia-interest-trends"
TIMEOUT_SECONDS = 600


def load_scenarios(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text())
    return {key: value for key, value in data.items() if not key.startswith("_")}


def claude_command(claude: str, prompt: str, model: str, skill_dir: Path, continue_: bool) -> list[str]:
    cmd = [claude, "-p", prompt, "--model", model, "--setting-sources", "project",
           "--output-format", "stream-json", "--verbose", "--add-dir", str(REPO),
           "--allowedTools", "Skill", "Read", f"Bash({skill_dir}/setup.sh)",
           f"Bash({skill_dir}/.venv/bin/python {skill_dir}/scripts/wit.py:*)"]
    if continue_:
        cmd.insert(3, "--continue")
    return cmd


def hide_paths(text: str, sandbox: Path) -> str:
    """Replace this run's sandbox paths (also macOS's /private/var form of /var) with placeholders."""
    # Longest first: /var/x is a substring of /private/var/x and would leave "/private<...>".
    for base in sorted({str(sandbox), str(sandbox.resolve())}, key=len, reverse=True):
        text = text.replace(f"{base}/.claude/skills/{SKILL_NAME}", "<SKILL_DIR>").replace(base, "<SANDBOX>")
    return text


def summary(raw: Path) -> dict:
    """Turns, cost, tool errors and grounding flags of one raw log."""
    info = {"turns": None, "cost": None, "tool_errors": 0}
    for line in raw.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            info["turns"], info["cost"] = event.get("num_turns"), event.get("total_cost_usd")
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if event.get("type") == "user" and isinstance(content, list):
            info["tool_errors"] += sum(1 for c in content if isinstance(c, dict) and c.get("is_error"))
    check = grounding.check(*grounding.read_transcript(raw))
    info["ungrounded"] = len(check["ungrounded_quotes"]) + len(check["ungrounded_numbers"])
    return info


def run(args: argparse.Namespace) -> int:
    scenarios = load_scenarios(args.scenarios_file)
    if args.list:
        for key, s in scenarios.items():
            print(f"{key:<5} [{s['set']}] {' / '.join(s['turns'])[:110]}")
        return 0
    selected = args.ids or [k for k, s in scenarios.items() if args.set in (None, s["set"])]
    unknown = [k for k in selected if k not in scenarios]
    if unknown:
        print(f"unknown scenario(s): {', '.join(unknown)}; see --list", file=sys.stderr)
        return 2
    if not args.dry_run and shutil.which(args.claude) is None:
        print(f"'{args.claude}' not found: install Claude Code or pass --claude <path>", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in selected:
        for n in range(1, args.runs + 1):
            # Resolved path: on macOS /var is a link to /private/var, and Claude Code reports the
            # resolved form; the allowlist must use the same form or setup.sh gets blocked.
            sandbox = Path(tempfile.mkdtemp(prefix=f"wit-{key}-")).resolve()
            skill_dir = sandbox / ".claude" / "skills" / SKILL_NAME
            skill_dir.parent.mkdir(parents=True)
            skill_dir.symlink_to(REPO, target_is_directory=True)
            turns = scenarios[key]["turns"]
            for t, prompt in enumerate(turns, start=1):
                name = f"{args.prefix}-{key}-run{n}" + (f"-turn{t}" if len(turns) > 1 else "")
                cmd = claude_command(args.claude, prompt, args.model, skill_dir, continue_=t > 1)
                if args.dry_run:
                    print(f"[{name}] cd {sandbox} && " + " ".join(json.dumps(c) if " " in c else c for c in cmd))
                    continue
                raw = out / f"{name}.jsonl"
                with raw.open("w") as log:
                    subprocess.run(cmd, cwd=sandbox, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=TIMEOUT_SECONDS, check=False)
                body = hide_paths(transcript.convert(raw.read_text().splitlines()), sandbox)
                (out / f"{name}.md").write_text(
                    f"# Run: {name}\n\n**Prompt:** {transcript.sanitize(prompt)}\n\n{body}\n")
                rows.append((name, summary(raw)))
                print(f"{name} done", flush=True)
            if not args.keep_sandboxes:
                shutil.rmtree(sandbox, ignore_errors=True)

    if rows:
        print(f"\n{'run':<42} {'turns':>5} {'cost':>8} {'tool errors':>11} {'ungrounded':>10}")
        for name, s in rows:
            cost = f"${s['cost']:.4f}" if s["cost"] is not None else "–"
            print(f"{name:<42} {s['turns'] or '–':>5} {cost:>8} {s['tool_errors']:>11} {s['ungrounded']:>10}")
        print("\nNext: score each transcript against evals/rubric.md "
              "(details of ungrounded items: uv run --locked python evals/grounding.py <run>.jsonl).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ids", nargs="*", help="scenario ids (default: all, or --set)")
    parser.add_argument("--set", choices=["examples", "holdout"], help="run every scenario of one set")
    parser.add_argument("--runs", type=int, default=2, help="runs per scenario (default 2)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"model id (default {DEFAULT_MODEL})")
    parser.add_argument("--prefix", default=datetime.date.today().isoformat(),
                        help="file name prefix (default: today's date)")
    parser.add_argument("--out", default=str(EVALS / "runs"), help="output folder (default evals/runs)")
    parser.add_argument("--scenarios-file", type=Path, default=EVALS / "scenarios.json")
    parser.add_argument("--claude", default="claude", help="path to the Claude Code CLI")
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    parser.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    parser.add_argument("--keep-sandboxes", action="store_true", help="keep the temporary sandbox folders")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
