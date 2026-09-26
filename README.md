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

## Usage

```bash
.venv/bin/python scripts/wit.py compare "intermittent fasting" --langs pl,cs --months 24
.venv/bin/python scripts/wit.py compare mercury --langs uk,en        # -> "ambiguous" + candidates
.venv/bin/python scripts/wit.py compare --qid Q308 --langs uk,en     # pick the planet
```

Prints one JSON object (per-language raw and normalized growth, notes, limitations) and
writes `chart.png`, `monthly.csv`, `result.json` and `query.json` to `output/<qid>-<label>/`.
API responses are cached in `.cache/`.

## Development

```bash
uv run --locked pytest                 # tests (installs the dev group)
uv run --locked scripts/wit.py --help  # run the CLI

# after changing dependencies:
uv lock
uv export --format requirements-txt --no-dev --no-emit-project -o requirements.txt
```

A test fails if `requirements.txt` is out of sync with `uv.lock`.
