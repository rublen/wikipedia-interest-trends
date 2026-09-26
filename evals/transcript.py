#!/usr/bin/env python3
"""Convert a `claude -p --output-format stream-json` log into a shareable Markdown transcript.

Keeps the prompt, tool calls, shortened tool results and the model's text. Drops session
metadata (connected accounts, session ids, tool lists) and images.

Usage: python evals/transcript.py runs/<run>.jsonl > runs/<run>.md
"""

from __future__ import annotations

import json
import sys

MAX_RESULT_CHARS = 1500


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(part.get("text", "[image]" if part.get("type") == "image" else "")
                     for part in content if isinstance(part, dict))


def convert(lines: list[str]) -> str:
    out = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            out.append(f"**Model:** `{event.get('model')}`\n")
        elif kind == "assistant":
            for part in event["message"]["content"]:
                if part["type"] == "text" and part["text"].strip():
                    out.append(f"### Assistant\n\n{part['text'].strip()}\n")
                elif part["type"] == "tool_use":
                    out.append(f"**Tool call — {part['name']}:**\n\n```json\n"
                               f"{json.dumps(part['input'], ensure_ascii=False, indent=1)}\n```\n")
        elif kind == "user":
            content = event["message"]["content"]
            if isinstance(content, str):
                out.append(f"### User\n\n{content}\n")
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    text = _text(part.get("content", ""))
                    if len(text) > MAX_RESULT_CHARS:
                        text = text[:MAX_RESULT_CHARS] + f"\n… [{len(text) - MAX_RESULT_CHARS} more chars]"
                    label = "Tool error" if part.get("is_error") else "Tool result"
                    out.append(f"<details><summary>{label}</summary>\n\n```\n{text}\n```\n</details>\n")
        elif kind == "result":
            out.append(f"---\n\nTurns: {event.get('num_turns')} · Duration: {event.get('duration_ms', 0) / 1000:.0f} s"
                       f" · Cost: ${event.get('total_cost_usd', 0):.4f}\n")
    return "\n".join(out)


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        print(convert(f.readlines()))
