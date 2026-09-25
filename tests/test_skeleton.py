import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import wit

ROOT = Path(__file__).resolve().parent.parent


def test_help_lists_planned_commands(capsys):
    assert wit.main([]) == 0
    out = capsys.readouterr().out
    for command in ("compare", "resolve", "fetch", "analyze"):
        assert command in out


def test_cli_runs_as_script_without_install():
    # Mirrors how the agent calls it: plain script path, no package install.
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "wit.py"), "--version"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.startswith("wit.py ")


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
def test_requirements_txt_matches_lockfile():
    exported = subprocess.run(
        ["uv", "export", "--format", "requirements-txt", "--no-dev",
         "--no-emit-project", "--locked", "--quiet"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout

    def body(text: str) -> list[str]:
        return [line for line in text.splitlines() if not line.startswith("#")]

    assert body(exported) == body((ROOT / "requirements.txt").read_text()), (
        "requirements.txt is stale; regenerate with: "
        "uv export --format requirements-txt --no-dev --no-emit-project -o requirements.txt"
    )
