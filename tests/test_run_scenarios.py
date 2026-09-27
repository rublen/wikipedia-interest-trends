"""The scenario runner, driven by a fake `claude` CLI (no network, no cost)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import run_scenarios  # noqa: E402

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_ARGV_LOG"], "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\n")
tool_out = json.dumps({"key_findings": ["Largest audience: ja (36,383 views/month)."]})
skill = os.path.join(os.getcwd(), ".claude/skills/wikipedia-interest-trends")
events = [
    {"type": "system", "subtype": "init", "model": "fake-model"},
    {"type": "system", "subtype": "notice", "message": "a plain-string message, as real logs have"},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",
        "input": {"command": skill + "/.venv/bin/python " + skill + "/scripts/wit.py compare x"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "content": tool_out}]}},
    {"type": "assistant", "message": {"content": [{"type": "text",
        "text": 'Key finding: "Largest audience: ja (36,383 views/month)."'}]}},
    {"type": "result", "num_turns": 3, "total_cost_usd": 0.0123, "result":
        'Key finding: "Largest audience: ja (36,383 views/month)."'},
]
for e in events:
    print(json.dumps(e))
'''


def test_runs_scenarios_and_writes_clean_transcripts(tmp_path, monkeypatch, capsys):
    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE)
    fake.chmod(0o755)
    argv_log = tmp_path / "argv.jsonl"
    monkeypatch.setenv("FAKE_ARGV_LOG", str(argv_log))
    scenarios = tmp_path / "scenarios.json"
    scenarios.write_text(json.dumps({"S1": {"set": "holdout", "turns": ["first question", "follow-up"]}}))
    out = tmp_path / "runs"

    code = run_scenarios.main(["S1", "--runs", "1", "--prefix", "t", "--out", str(out),
                               "--scenarios-file", str(scenarios), "--claude", str(fake)])
    assert code == 0
    calls = [json.loads(line) for line in argv_log.read_text().splitlines()]
    assert len(calls) == 2
    assert "--continue" not in calls[0]["argv"] and "--continue" in calls[1]["argv"]
    assert calls[0]["cwd"] == calls[1]["cwd"]  # both turns in the same sandbox
    assert "--setting-sources" in calls[0]["argv"] and "Skill" in calls[0]["argv"]
    for turn in (1, 2):
        md = (out / f"t-S1-run1-turn{turn}.md").read_text()
        assert (out / f"t-S1-run1-turn{turn}.jsonl").exists()
        assert " <SKILL_DIR>/scripts/wit.py" in md and "<SKILL_DIR>/.venv/bin/python" in md
        assert "/var/" not in md and "/tmp/" not in md and "/private" not in md
    report = capsys.readouterr().out
    assert "t-S1-run1-turn2" in report and "$0.0123" in report
    assert report.splitlines()[-3].split()[-1] == "0"  # no ungrounded quotes or numbers


def test_list_and_dry_run(capsys):
    assert run_scenarios.main(["--list"]) == 0
    listed = capsys.readouterr().out
    assert "H4" in listed and "ex3" in listed
    assert run_scenarios.main(["H7", "--runs", "1", "--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert printed.count("[") == 2 and "--continue" in printed.splitlines()[1]
