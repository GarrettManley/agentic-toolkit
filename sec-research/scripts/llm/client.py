# scripts/llm/client.py
"""Provider-agnostic LLM client. One method (complete_json); two adapters
(Claude default, llama opt-in) selected by select_client(). Default provider is
env SECRESEARCH_LLM_PROVIDER (default "claude")."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

DEFAULT_PROVIDER = "claude"


class LLMConfigError(RuntimeError):
    """Misconfiguration: unknown provider, missing API key, etc."""


class LLMUnavailable(RuntimeError):
    """The provider could not be reached / returned an unusable response."""


@dataclass(frozen=True)
class ChatResponse:
    text: str                 # raw assistant output — a JSON string ({"hypotheses": [...]})
    provider: str
    model: str
    finish_reason: str | None
    usage: dict | None


@runtime_checkable
class LLMClient(Protocol):
    provider: str

    def complete_json(self, *, system: str, messages: list[dict], schema: dict,
                      max_tokens: int = 4096, temperature: float = 0.0,
                      timeout: float = 120.0, from_fixture: str | None = None) -> ChatResponse: ...


def select_client(provider: str | None = None) -> LLMClient:
    name = (provider or os.environ.get("SECRESEARCH_LLM_PROVIDER") or DEFAULT_PROVIDER).lower()
    if name == "claude":
        from llm.providers.claude import ClaudeApiClient
        return ClaudeApiClient()
    if name == "llama":
        from llm.providers.llama import LlamaServerClient
        return LlamaServerClient()
    raise LLMConfigError(f"unknown LLM provider {name!r} (expected 'claude' or 'llama')")
