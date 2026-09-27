"""The eval grounding check: catches invented quotes and numbers, tolerates harmless edits."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import grounding  # noqa: E402

TOOL_OUTPUT = json.dumps({
    "key_findings": ["Analyzing: “English” (Q1860), West Germanic language.",
                     "Largest audience: ja (36,383 views/month); smallest: uk (6,659 views/month)."],
    "line": "no clear change with medium confidence (probably real, but weakened by the reasons listed): "
            "share moved 0.7%, within the ±4% normal fluctuation; 23,477 views/month.",
    "reason": "the share was lower than in the same month a year earlier in 10 of 12 months",
    "period": "2024-09..2025-08 vs 2025-09..2026-08",
}, ensure_ascii=False)


def transcript(tmp_path, answer: str) -> Path:
    events = [
        {"type": "user", "message": {"content": "Compare English in uk and ja"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": TOOL_OUTPUT}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": answer}]}},
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events))
    return path


def run(tmp_path, answer):
    return grounding.check(*grounding.read_transcript(transcript(tmp_path, answer)))


def test_verbatim_quotes_with_different_quote_marks_pass(tmp_path):
    r = run(tmp_path, 'As the tool says: "Analyzing: \'English\' (Q1860), West Germanic language." and '
                      '"**Largest audience:** ja (36,383 views/month); smallest: uk (6,659 views/month)."')
    assert r["ungrounded_quotes"] == [] and r["edited_quotes"] == []


def test_trimmed_quote_is_edited_not_ungrounded(tmp_path):
    r = run(tmp_path, '"no clear change with medium confidence: share moved 0.7%, within the ±4% normal '
                      'fluctuation; 23,477 views/month"')
    assert r["ungrounded_quotes"] == [] and len(r["edited_quotes"]) == 1


def test_invented_quote_is_ungrounded(tmp_path):
    r = run(tmp_path, '"The stable ones represent the most reliable audiences for a language-learning app." — recommendation')
    assert len(r["ungrounded_quotes"]) == 1


def test_n_of_m_phrases_and_numbers(tmp_path):
    r = run(tmp_path, "The share fell in 14 of 12 months; Japan has about 36K views/month and 999 fans, "
                      "compared over 2025-09..2026-08 (Sept 2025–Aug 2026). The share was lower in 10 of 12 months.")
    assert r["ungrounded_numbers"] == ["14 of 12", "999"]  # 36K is a rounded 36,383; dates are found
