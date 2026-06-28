"""Vision provider abstraction: one interface, two backends (Claude + OpenAI).

Each backend takes a system prompt, a user instruction, and a base64 PNG, and returns a
JSON object (the structured puzzle). Both are asked for strict JSON; the caller validates
it against the schema. API keys come from the environment
(``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``).
"""

from __future__ import annotations

import base64
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ProviderError(RuntimeError):
    pass


def encode_image(path: str | Path) -> str:
    return base64.standard_b64encode(Path(path).read_bytes()).decode()


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first balanced JSON object out of a model response."""
    start = text.find("{")
    if start == -1:
        raise ProviderError(f"no JSON object in model output: {text[:200]!r}")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ProviderError("unbalanced JSON in model output")


class VisionProvider(ABC):
    name: str
    default_model: str

    def __init__(self, model: str | None = None):
        self.model = model or self.default_model

    @abstractmethod
    def extract(self, *, system: str, instruction: str, image_b64: str) -> dict[str, Any]: ...


class ClaudeProvider(VisionProvider):
    name = "claude"
    default_model = "claude-opus-4-8"

    def extract(self, *, system: str, instruction: str, image_b64: str) -> dict[str, Any]:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("pip/uv add anthropic to use the Claude provider") from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": instruction},
                    ],
                }
            ],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return _extract_json(text)


class OpenAIProvider(VisionProvider):
    name = "openai"
    default_model = "gpt-4o"

    def extract(self, *, system: str, instruction: str, image_b64: str) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("pip/uv add openai to use the OpenAI provider") from exc
        if not os.environ.get("OPENAI_API_KEY"):
            raise ProviderError("OPENAI_API_KEY is not set")
        client = OpenAI()
        resp = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                },
            ],
        )
        return _extract_json(resp.choices[0].message.content or "")


_PROVIDERS: dict[str, type[VisionProvider]] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str, model: str | None = None) -> VisionProvider:
    if name not in _PROVIDERS:
        raise ProviderError(f"unknown provider {name!r}; choose from {list(_PROVIDERS)}")
    return _PROVIDERS[name](model=model)
