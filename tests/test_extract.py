"""Extraction plumbing — exercised without any API key.

We can't call a real vision model in tests, but we can prove the surrounding
machinery works: pulling JSON out of a noisy model response, the provider registry,
and the extract → (optional review) flow driven by a fake provider.
"""

from __future__ import annotations

import pytest

from murbo import extract as extract_mod
from murbo.providers import (
    ClaudeProvider,
    MiniMaxProvider,
    OpenAIProvider,
    ProviderError,
    _extract_json,
    get_provider,
)


def test_extract_json_plain():
    assert _extract_json('{"a": 1, "b": [2, 3]}') == {"a": 1, "b": [2, 3]}


def test_extract_json_from_fenced_prose():
    text = 'Sure! Here it is:\n```json\n{"id": "x", "nested": {"k": "}"}}\n```\nHope that helps.'
    assert _extract_json(text) == {"id": "x", "nested": {"k": "}"}}


def test_extract_json_handles_braces_inside_strings():
    assert _extract_json('{"s": "a{b}c", "n": 1}') == {"s": "a{b}c", "n": 1}


def test_extract_json_no_object_raises():
    with pytest.raises(ProviderError):
        _extract_json("there is no json here")


def test_provider_registry():
    assert isinstance(get_provider("claude"), ClaudeProvider)
    assert isinstance(get_provider("minimax"), MiniMaxProvider)
    assert isinstance(get_provider("openai"), OpenAIProvider)
    assert get_provider("claude", model="custom").model == "custom"
    assert get_provider("minimax").model == "MiniMax-M3"
    with pytest.raises(ProviderError):
        get_provider("nope")


def test_minimax_requires_api_key(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="MINIMAX_API_KEY"):
        get_provider("minimax").extract(system="s", instruction="i", image_b64="x")


class _FakeProvider:
    def __init__(self):
        self.calls = []

    def extract(self, *, system, instruction, image_b64):
        self.calls.append(instruction)
        return {"id": "fake", "title": "Fake", "grid": {"rows": 1, "cols": 1}}


def test_extract_puzzle_uses_provider(monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(extract_mod, "get_provider", lambda *a, **k: fake)
    monkeypatch.setattr("murbo.providers.encode_image", lambda path: "ZmFrZQ==")

    out = extract_mod.extract_puzzle("whatever.png", provider="claude")
    assert out["id"] == "fake"
    assert len(fake.calls) == 1  # single pass


def test_extract_puzzle_review_does_second_pass(monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(extract_mod, "get_provider", lambda *a, **k: fake)
    monkeypatch.setattr("murbo.providers.encode_image", lambda path: "ZmFrZQ==")

    extract_mod.extract_puzzle("whatever.png", provider="claude", review=True)
    assert len(fake.calls) == 2  # extract + review


def test_normalize_drops_null_room_category_but_keeps_clue_nulls():
    puzzle = {
        "rooms": [
            {"name": "A", "category": None, "cells": []},
            {"name": "B", "category": "store", "cells": []},
        ],
        "suspects": [
            {
                "id": "x",
                "clues": [{"type": "object_offset", "object": "bear", "dRow": -4, "dCol": None}],
            }
        ],
    }
    out = extract_mod._normalize(puzzle)
    assert "category" not in out["rooms"][0]  # null optional dropped
    assert out["rooms"][1]["category"] == "store"  # real value kept
    assert out["suspects"][0]["clues"][0]["dCol"] is None  # meaningful clue null preserved


def test_minimax_uses_thinking_and_large_budget():
    from murbo.providers import MiniMaxProvider

    p = MiniMaxProvider()
    assert p.extra_body == {"thinking": {"type": "adaptive"}}
    assert p.max_tokens >= 32000
