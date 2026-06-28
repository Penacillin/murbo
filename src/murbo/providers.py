"""Vision provider abstraction: one interface, three backends (Claude + MiniMax + OpenAI).

Each backend takes a system prompt, a user instruction, and a base64 PNG, and returns a
JSON object (the structured puzzle). All are asked for strict JSON; the caller validates
it against the schema. API keys come from the environment
(``ANTHROPIC_API_KEY`` / ``MINIMAX_API_KEY`` / ``OPENAI_API_KEY``).

MiniMax exposes an Anthropic-compatible Messages endpoint, so it reuses the ``anthropic``
SDK pointed at MiniMax's ``base_url``.
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


class _AnthropicCompatProvider(VisionProvider):
    """Shared logic for any Anthropic Messages-API-compatible backend.

    Subclasses set ``name``/``default_model`` and implement :meth:`_client`, which
    returns a configured ``anthropic.Anthropic`` (Claude defaults; MiniMax overrides
    ``base_url`` + ``api_key``).
    """

    env_key: str
    max_tokens: int = 16000
    # Extra request-body fields merged into the Messages call (e.g. MiniMax's `thinking`).
    extra_body: dict[str, Any] | None = None

    def _client(self) -> Any:
        if not os.environ.get(self.env_key):
            raise ProviderError(f"{self.env_key} is not set")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(f"uv add anthropic to use the {self.name} provider") from exc
        return anthropic.Anthropic()

    def extract(self, *, system: str, instruction: str, image_b64: str) -> dict[str, Any]:
        client = self._client()
        kwargs: dict[str, Any] = {}
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
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
            **kwargs,
        )
        # Skip any non-text blocks (e.g. extended-thinking blocks); the JSON is in the text.
        text = "".join(block.text for block in msg.content if block.type == "text")
        if not text.strip():
            reason = getattr(msg, "stop_reason", None)
            hint = (
                " (response hit max_tokens — thinking likely consumed the whole budget; "
                "raise max_tokens or disable review)"
                if reason == "max_tokens"
                else ""
            )
            raise ProviderError(f"model returned no text (stop_reason={reason!r}){hint}")
        return _extract_json(text)


class ClaudeProvider(_AnthropicCompatProvider):
    name = "claude"
    default_model = "claude-opus-4-8"
    env_key = "ANTHROPIC_API_KEY"


class MiniMaxProvider(_AnthropicCompatProvider):
    name = "minimax"
    default_model = "MiniMax-M3"  # the multimodal model (text + image)
    env_key = "MINIMAX_API_KEY"
    base_url = "https://api.minimax.io/anthropic"
    # Adaptive thinking markedly improves the careful grid/room tracing this task needs;
    # the larger budget must cover the thinking tokens AND the JSON that follows.
    max_tokens = 48000
    extra_body = {"thinking": {"type": "adaptive"}}

    def _client(self) -> Any:
        api_key = os.environ.get(self.env_key)
        if not api_key:
            raise ProviderError(f"{self.env_key} is not set")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("uv add anthropic to use the MiniMax provider") from exc
        # Explicit timeout: thinking + a large max_tokens would otherwise trip the SDK's
        # "streaming required for >10min" guard.
        return anthropic.Anthropic(
            base_url=self.base_url, api_key=api_key, max_retries=2, timeout=600.0
        )


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
    "minimax": MiniMaxProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str, model: str | None = None) -> VisionProvider:
    if name not in _PROVIDERS:
        raise ProviderError(f"unknown provider {name!r}; choose from {list(_PROVIDERS)}")
    return _PROVIDERS[name](model=model)
