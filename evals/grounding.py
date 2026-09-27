#!/usr/bin/env python3
"""Grounding check for agent answers: are quotes and numbers traceable to what the model received?

Usage: uv run --locked python evals/grounding.py <transcript.jsonl> [...]
(`claude -p --output-format stream-json` logs and Claude Code session logs both work.)

What it checks, against everything the model received (tool results, the skill text, the
user's prompt):
- **Quotes:** every string in quotation marks (4+ words), sentence by sentence, is classed as
  *verbatim* (found as is, after normalizing whitespace, markdown emphasis, quote and dash
  styles, and arrows), *edited* (not verbatim, but every clause of it is found: e.g. a bracket
  left out) or *ungrounded* (some clause appears nowhere: invented). Only ungrounded quotes
  count as failures; edited quotes are listed for information.
- **Numbers:** "N of M" phrases must appear as phrases (so "14 of 12 months" fails even though
  14 and 12 occur elsewhere); every other number must occur as a value somewhere in the input
  ("23K" and "~12.5K" are accepted within 5% of a number that occurs).

What it does NOT catch, and still needs a human reader with evals/rubric.md:
- paraphrases without quotation marks, and correct numbers attached to wrong words
  ("German has the largest audience (3rd overall)": 3rd is in the output, "largest" is wrong);
- judgment items: invented reasons (G8), go/no-go advice (G10), wrong verdicts stated in words;
- directions: the sign of a number is ignored, so "fell 11%" and "-11%" both match 11.

It is a grading tool for the evals. Running the same check inside the skill, so the agent
verifies its answer before sending it, is on the roadmap ("guards belong in code").
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MIN_QUOTE_WORDS = 4
ROUNDED_TOLERANCE = 0.05


def normalize(text: str) -> str:
    text = text.replace('\\"', '"').replace("\\n", " ")
    for a, b in [("“", "'"), ("”", "'"), ("‘", "'"), ("’", "'"), ('"', "'"), ("→", "->"),
                 ("—", "-"), ("–", "-"), ("−", "-"), ("…", "...")]:
        text = text.replace(a, b)
    text = re.sub(r"[*_`]", "", text)          # markdown emphasis and code marks
    return re.sub(r"\s+", " ", text).strip().lower()


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(part.get("text", part.get("content", ""))) for part in content
                         if isinstance(part, dict))
    return ""


def read_transcript(path: Path) -> tuple[str, str]:
    """(everything the model received, the final answer)."""
    received, answers, final = [], [], None
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind, message = event.get("type"), event.get("message") or {}
        if kind == "user":
            received.append(_text(message.get("content")))
        elif kind == "assistant":
            content = message.get("content", [])
            if any(part.get("type") == "tool_use" for part in content if isinstance(part, dict)):
                answers = []  # text before a tool call is narration, not the answer
            answers += [part["text"] for part in content
                        if isinstance(part, dict) and part.get("type") == "text"]
        elif kind == "result" and event.get("result"):
            final = event["result"]
    return "\n".join(received), final if final is not None else "\n".join(answers)


QUOTE = re.compile(r'"([^"\n]{8,}?)"')


def quotes(answer: str) -> list[str]:
    found = []
    for match in QUOTE.findall(normalize_quotes_only(answer)):
        for part in re.split(r"\.\.\.|…", match):
            part = part.strip(" .,;:")
            if len(part.split()) >= MIN_QUOTE_WORDS:
                found.append(part)
    return found


def normalize_quotes_only(text: str) -> str:
    return text.replace("“", '"').replace("”", '"')


NUMBER = re.compile(r"(?<![\w.])[±~≈]?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kK]\b)?")
N_OF_M = re.compile(r"\b\d+ of \d+\b")


def _values(text: str) -> set[float]:
    """Every number in the input, found loosely (also inside dates like 2025-09..2026-08)."""
    return {float(n.replace(",", "")) for n in re.findall(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?", text)}


def _clauses(quote: str) -> list[str]:
    return [c.strip(" .,'") for c in re.split(r"[;:()]|\. ", quote) if len(c.split()) >= 3]


def classify(quote: str, source: str) -> str:
    """'verbatim', 'edited' or 'ungrounded', judged sentence by sentence."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", quote) if s.strip()]
    kinds = []
    for sentence in sentences:
        sentence = normalize(sentence).strip(" .")
        if not sentence or sentence in source:
            kinds.append("verbatim")
        elif all(clause in source for clause in _clauses(sentence)):
            kinds.append("edited")
        else:
            kinds.append("ungrounded")
    return "ungrounded" if "ungrounded" in kinds else "edited" if "edited" in kinds else "verbatim"


def check(received: str, answer: str) -> dict:
    source = normalize(received)
    found = quotes(answer)
    kinds = {q: classify(q, source) for q in found}
    missing_quotes = [q for q in found if kinds[q] == "ungrounded"]
    edited_quotes = [q for q in found if kinds[q] == "edited"]

    values = _values(received)
    missing_numbers = []
    plain = normalize(answer)
    for phrase in N_OF_M.findall(plain):
        if phrase not in source:
            missing_numbers.append(phrase)
    plain = N_OF_M.sub(" ", plain)
    plain = re.sub(r"\b\d{4}-\d{2}(\.\.\d{4}-\d{2})?\b", " ", plain)  # dates like 2025-09
    plain = re.sub(r"^\s*\d+\.\s", " ", plain)                        # list numbering
    for match in NUMBER.finditer(plain):
        value = float(match.group(1).replace(",", ""))
        if match.group(2):  # 23K -> rounded thousands
            value *= 1000
            ok = any(abs(v - value) <= ROUNDED_TOLERANCE * value for v in values)
        else:
            ok = value in values or any(abs(v - value) <= ROUNDED_TOLERANCE * value
                                        for v in values if match.group(0).startswith(("~", "≈")))
        if not ok:
            missing_numbers.append(match.group(0).strip())
    return {"quotes_checked": len(found), "ungrounded_quotes": missing_quotes,
            "edited_quotes": edited_quotes,
            "numbers_checked": len(NUMBER.findall(plain)) + len(N_OF_M.findall(normalize(answer))),
            "ungrounded_numbers": sorted(set(missing_numbers), key=missing_numbers.index)}


def main(paths: list[str]) -> int:
    worst = 0
    for path in paths:
        received, answer = read_transcript(Path(path))
        result = check(received, answer)
        print(f"== {path}")
        print(f"   quotes: {result['quotes_checked']} checked, {len(result['edited_quotes'])} edited "
              f"(all parts found), {len(result['ungrounded_quotes'])} UNGROUNDED")
        for q in result["ungrounded_quotes"]:
            print(f"     - \"{q[:200]}\"")
        print(f"   numbers: {result['numbers_checked']} checked, "
              f"{len(result['ungrounded_numbers'])} not found: {result['ungrounded_numbers']}")
        worst = max(worst, 1 if result["ungrounded_quotes"] or result["ungrounded_numbers"] else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
