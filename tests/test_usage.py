from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from brief.usage import UsageError, load_pricing, measure

SINCE = datetime.fromisoformat("2026-10-27T10:00:00Z")
UNTIL = datetime.fromisoformat("2026-10-27T11:00:00Z")


def _entry(message_id: str, timestamp: str, content: list, model: str = "claude-opus-5-5") -> dict:
    usage = {
        "input_tokens": 2,
        "cache_creation_input_tokens": 1_000,
        "cache_read_input_tokens": 100_000,
        "output_tokens": 500,
        "cache_creation": {"ephemeral_5m_input_tokens": 1_000, "ephemeral_1h_input_tokens": 0},
    }
    return {"type": "assistant", "timestamp": timestamp, "message": {"id": message_id, "model": model, "usage": usage, "content": content}}


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n{truncated", encoding="utf-8")
    return path


def test_counts_each_message_once_and_every_search(tmp_path: Path) -> None:
    search = {"type": "tool_use", "id": "toolu_1", "name": "WebSearch", "input": {}}
    entries = [
        # One message logged as two blocks: usage repeats, the search appears once.
        _entry("msg_a", "2026-10-27T10:05:00Z", [{"type": "text", "text": "looking"}]),
        _entry("msg_a", "2026-10-27T10:05:01Z", [search]),
        _entry("msg_b", "2026-10-27T10:06:00Z", [{"type": "text", "text": "done"}]),
        _entry("msg_old", "2026-10-27T09:00:00Z", [{"type": "text", "text": "before the window"}]),
        {"type": "user", "timestamp": "2026-10-27T10:05:30Z", "message": {"content": "tool result"}},
    ]
    part = measure("session", SINCE, UNTIL, [_write(tmp_path, entries)], load_pricing())
    (model,) = part.models
    assert model.requests == 2
    assert (model.tokens.cache_read, model.tokens.output, model.tokens.web_searches) == (200_000, 1_000, 1)
    # 2 x (2 x $4 + 1,000 x $5 + 100,000 x $0.20 + 500 x $20) per million, plus one search at $10 per thousand.
    assert model.cost_usd == pytest.approx(2 * (8 + 5_000 + 20_000 + 10_000) / 1e6 + 0.01, abs=1e-4)
    assert part.total_tokens == 2 * (2 + 1_000 + 100_000 + 500)


def test_unknown_model_is_an_error(tmp_path: Path) -> None:
    path = _write(tmp_path, [_entry("msg_a", "2026-10-27T10:05:00Z", [], model="claude-unknown")])
    with pytest.raises(UsageError, match="no price for model 'claude-unknown'"):
        measure("session", SINCE, UNTIL, [path], load_pricing())
