---
name: wikipedia-interest-trends
description: Analyze how interest in a topic changes over time across Wikipedia language editions, using Wikimedia pageview data. Use when the user asks which topics, courses or markets/languages to pursue, wants to compare interest in a topic between languages or over time, or needs a chart or short shareable report (PDF) backed by Wikipedia pageviews.
---

# Wikipedia Interest Trends

Status: skeleton (iteration 0). Analysis commands are not implemented yet.

## Setup (once)

Run all commands from this skill's directory.

```bash
./setup.sh
```

- Exit code 0: ready.
- Exit code 3: neither uv nor Python 3.11+ is installed. Show the user the install
  command that `setup.sh` printed and **ask for permission** before running it. Never
  install anything without asking.

## Usage

```bash
.venv/bin/python scripts/wit.py --help
```

Always use `.venv/bin/python`, not a system `python`.
