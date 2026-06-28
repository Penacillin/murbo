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
    assert isinstance(get_provider("openai"), OpenAIProvider)
    assert get_provider("claude", model="custom").model == "custom"
    with pytest.raises(ProviderError):
        get_provider("nope")


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
