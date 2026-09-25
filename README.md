# wikipedia-interest-trends

An [Agent Skill](https://agentskills.io) that analyzes Wikipedia pageview trends across
topics and language editions. It helps B2C founders decide which topics to develop and
which languages to launch in. The repository root is the skill directory; the agent
entry point is [`SKILL.md`](SKILL.md). The roadmap is in [`PLAN.md`](PLAN.md).

## Requirements

**uv, or Python 3.11+**, plus a POSIX shell (macOS or Linux). Network access to
`wikimedia.org` and `wikidata.org`. Windows is not supported yet, and the lockfile
covers only macOS and Linux (`[tool.uv] environments` in `pyproject.toml`).

## Setup

```bash
./setup.sh
```

| Situation | What `setup.sh` does |
|---|---|
| `uv` found | `uv sync --locked --no-dev` (main path) |
| no uv, Python ≥ 3.11 found | `python3 -m venv .venv` + `pip install -r requirements.txt` (pinned, hashed) |
| neither | exits with code 3 and prints the uv install command; installs nothing |

Both paths create `.venv/`. Run the CLI with `.venv/bin/python scripts/wit.py --help`.
`WIT_SETUP=pip ./setup.sh` forces the fallback path.

## Development

```bash
uv run --locked pytest                 # tests (installs the dev group)
uv run --locked scripts/wit.py --help  # run the CLI

# after changing dependencies:
uv lock
uv export --format requirements-txt --no-dev --no-emit-project -o requirements.txt
```

A test fails if `requirements.txt` is out of sync with `uv.lock`.
