# scripts/llm/providers/claude.py
"""Claude Messages API adapter. Forces a single tool (emit_hypotheses) whose
input_schema is the wrapper schema, so output is structurally constrained. Key
via keyring('anthropic','api-key') with ANTHROPIC_API_KEY env fallback; never
logged or persisted."""
from __future__ import annotations

import json
import os

from llm._hosts import CLAUDE_BOOTSTRAP_HOSTS
from llm._http import post_json
from llm.client import ChatResponse, LLMConfigError, LLMUnavailable

ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = os.environ.get("SECRESEARCH_CLAUDE_MODEL", "claude-sonnet-4-6")
TOOL_NAME = "emit_hypotheses"


def _resolve_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import keyring
        key = keyring.get_password("anthropic", "api-key")
    except Exception:
        key = None
    if not key:
        raise LLMConfigError(
            "no Anthropic API key: set ANTHROPIC_API_KEY or "
            "keyring.set_password('anthropic','api-key', <key>)")
    return key


class ClaudeApiClient:
    provider = "claude"

    def __init__(self, *, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self._api_key = api_key  # lazy: only resolved on a live call

    def _headers(self) -> dict:
        return {"x-api-key": self._api_key or _resolve_key(),
                "anthropic-version": ANTHROPIC_VERSION}

    def build_payload(self, *, system: str, messages: list[dict], schema: dict,
                      max_tokens: int, temperature: float) -> dict:
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages,
            "tools": [{"name": TOOL_NAME,
                       "description": "Emit candidate vulnerability hypotheses.",
                       "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
        }

    def parse_response(self, raw: dict) -> ChatResponse:
        blocks = [b for b in raw.get("content", []) if b.get("type") == "tool_use"]
        if not blocks:
            raise LLMUnavailable("Claude response had no tool_use block")
        return ChatResponse(text=json.dumps(blocks[0]["input"]), provider=self.provider,
                            model=raw.get("model", self.model),
                            finish_reason=raw.get("stop_reason"), usage=raw.get("usage"))

    def complete_json(self, *, system: str, messages: list[dict], schema: dict,
                      max_tokens: int = 4096, temperature: float = 0.0,
                      timeout: float = 120.0, from_fixture: str | None = None) -> ChatResponse:
        payload = self.build_payload(system=system, messages=messages, schema=schema,
                                     max_tokens=max_tokens, temperature=temperature)
        headers = None if from_fixture is not None else self._headers()
        raw = post_json(ENDPOINT, payload, bootstrap_hosts=CLAUDE_BOOTSTRAP_HOSTS,
                        headers=headers, from_fixture=from_fixture, timeout=timeout)
        return self.parse_response(raw)
