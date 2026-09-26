#!/usr/bin/env bash
# Prepare the skill's Python environment in .venv/ (idempotent).
#
#   1. uv found                  -> uv sync --locked --no-dev        (main path)
#   2. no uv, python3 >= 3.11    -> venv + pip install -r requirements.txt (pinned fallback)
#   3. neither                   -> exit 3; nothing is installed silently.
#
# Either way, run the skill with: .venv/bin/python scripts/wit.py ...
# Set WIT_SETUP=pip to force the fallback path (useful for testing it).

set -euo pipefail

EXIT_NO_TOOLCHAIN=3
MIN_MINOR=11

cd "$(dirname "$0")"

find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, $MIN_MINOR) else 1)" 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

if [[ "${WIT_SETUP:-}" != "pip" ]] && command -v uv >/dev/null 2>&1; then
    echo "setup: using uv ($(uv --version))" >&2
    uv sync --locked --no-dev --quiet
elif python_bin="$(find_python)"; then
    echo "setup: uv not used; falling back to $python_bin ($("$python_bin" --version)) + pip" >&2
    if [[ ! -x .venv/bin/python ]]; then
        "$python_bin" -m venv .venv
    fi
    # A .venv created earlier by uv has no pip; bootstrap it.
    .venv/bin/python -m pip --version >/dev/null 2>&1 || .venv/bin/python -m ensurepip --upgrade >/dev/null
    .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
else
    cat >&2 <<'EOF'
setup: FAILED - neither uv nor Python 3.11+ was found.
Install uv (recommended), then rerun ./setup.sh:
    curl -LsSf https://astral.sh/uv/install.sh | sh
(or on macOS: brew install uv)
Agent: show this command to the user and ask for permission before running it.
EOF
    exit "$EXIT_NO_TOOLCHAIN"
fi

.venv/bin/python scripts/wit.py --version >/dev/null
# Print the exact absolute command so an agent can copy it instead of assembling paths.
echo "setup: OK - run the skill with exactly this command prefix:" >&2
echo "$PWD/.venv/bin/python $PWD/scripts/wit.py" >&2
