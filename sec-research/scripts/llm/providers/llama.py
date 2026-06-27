# scripts/llm/providers/llama.py
"""llama-server adapter (OpenAI-compatible /v1/chat/completions). Uses
response_format json_schema so llama-server grammar-constrains the output. Local
loopback egress, gated for audit symmetry via LLAMA_BOOTSTRAP_HOSTS."""
from __future__ import annotations

import os

from llm._hosts import LLAMA_BOOTSTRAP_HOSTS
from llm._http import post_json
from llm.client import ChatResponse, LLMUnavailable

ENDPOINT = os.environ.get("SECRESEARCH_LLAMA_ENDPOINT",
                          "http://127.0.0.1:8080/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("SECRESEARCH_LLAMA_MODEL", "local")


class LlamaServerClient:
    provider = "llama"

    def __init__(self, *, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL

    def preflight(self) -> None:
        """Confirm the local llama-server is reachable via its /health endpoint.
        Raises LLMUnavailable if not. Loopback only — no token cost."""
        import urllib.request

        health = ENDPOINT.rsplit("/v1/", 1)[0] + "/health"
        try:
            with urllib.request.urlopen(health, timeout=5) as r:  # noqa: S310 (loopback)
                if r.status != 200:
                    raise LLMUnavailable(f"llama-server /health returned {r.status}")
        except LLMUnavailable:
            raise
        except Exception as e:  # URLError, socket timeout, etc.
            raise LLMUnavailable(f"llama-server unreachable at {health}: {e}") from e

    def build_payload(self, *, system: str, messages: list[dict], schema: dict,
                      max_tokens: int, temperature: float) -> dict:
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system}, *messages],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "hypotheses",
                                                "schema": schema, "strict": True}},
        }

    def parse_response(self, raw: dict) -> ChatResponse:
        choices = raw.get("choices") or []
        if not choices:
            raise LLMUnavailable("llama response had no choices")
        choice = choices[0]
        return ChatResponse(text=choice["message"]["content"], provider=self.provider,
                            model=raw.get("model", self.model),
                            finish_reason=choice.get("finish_reason"), usage=raw.get("usage"))

    def complete_json(self, *, system: str, messages: list[dict], schema: dict,
                      max_tokens: int = 4096, temperature: float = 0.0,
                      timeout: float = 120.0, from_fixture: str | None = None) -> ChatResponse:
        payload = self.build_payload(system=system, messages=messages, schema=schema,
                                     max_tokens=max_tokens, temperature=temperature)
        raw = post_json(ENDPOINT, payload, bootstrap_hosts=LLAMA_BOOTSTRAP_HOSTS,
                        from_fixture=from_fixture, timeout=timeout)
        return self.parse_response(raw)
