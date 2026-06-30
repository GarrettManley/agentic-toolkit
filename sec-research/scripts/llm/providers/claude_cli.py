# scripts/llm/providers/claude_cli.py
"""Claude Code CLI adapter (`claude -p`, headless). Authors via the subscription
OAuth session's *programmatic credit pool*, not the metered Messages API. Two
responsibilities the HTTP adapters get for free: (1) strip ANTHROPIC_API_KEY /
ANTHROPIC_AUTH_TOKEN from the subprocess env so the CLI uses the credit pool, never
metered billing; (2) harden JSON — `--output-format json` wraps un-grammar-constrained
model text, so we extract + validate it here. Fail-closed: any CLI error (incl. an
exhausted pool) raises; we never spill to the metered API."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from llm.client import ChatResponse, LLMConfigError, LLMUnavailable

DEFAULT_MODEL = os.environ.get("SECRESEARCH_CLAUDE_CLI_MODEL", "sonnet")
CLI_BIN = os.environ.get("SECRESEARCH_CLAUDE_CLI_BIN", "claude")
_STRIP_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
_FENCE = re.compile(r"^```[a-zA-Z0-9]*\n(.*)\n```$", re.DOTALL)
_POOL_TOKENS = ("credit", "quota", "usage limit", "rate limit", "exhaust")
_log = logging.getLogger(__name__)


def _default_runner(argv, *, input, env, timeout):
    # Resolve the binary via shutil.which (honors PATHEXT) and pass the resolved full
    # path as argv[0]: `claude` is very likely an npm .cmd/.ps1 shim on Windows, and
    # subprocess.run(["claude", ...]) raises FileNotFoundError for shim binaries — the
    # well-known CPython Windows .cmd/.bat subprocess gap. shell=False stays load-bearing
    # throughout (do NOT use shell=True — prompt text flows through `input`, and shell=True
    # would reopen command injection risk).
    resolved = shutil.which(argv[0]) or argv[0]
    return subprocess.run([resolved, *argv[1:]], input=input, env=env, timeout=timeout,
                          capture_output=True, text=True, shell=False)


def _extract_json(text: str) -> dict:
    s = text.strip()
    m = _FENCE.match(s)
    if m:
        s = m.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(s[start:end + 1])
            except json.JSONDecodeError as e:
                raise LLMUnavailable(f"claude CLI result was not valid JSON: {e}") from e
        raise LLMUnavailable("claude CLI result contained no JSON object")


def _require_keys(obj, schema: dict) -> None:
    if not isinstance(obj, dict):
        raise LLMUnavailable(f"claude CLI JSON was {type(obj).__name__}, expected object")
    missing = [k for k in schema.get("required", []) if k not in obj]
    if missing:
        raise LLMUnavailable(f"claude CLI JSON missing required keys: {missing}")


def _find_event(events, type_name: str) -> dict | None:
    # `claude -p --output-format json` emits a JSON ARRAY of session events
    # (system/assistant/rate_limit_event/result/...), confirmed empirically in
    # Task 1's spike — not a single envelope object as originally assumed. Accept
    # a bare dict too (wrapped as a 1-element list) for hand-built test convenience.
    if isinstance(events, dict):
        events = [events]
    matches = [e for e in events if isinstance(e, dict) and e.get("type") == type_name]
    return matches[-1] if matches else None


def _classify_failure(proc) -> Exception:
    blob = ((proc.stdout or "") + " " + (proc.stderr or "")).lower()
    if any(t in blob for t in _POOL_TOKENS):
        return LLMConfigError(
            "claude CLI: programmatic credit pool appears exhausted or rate-limited. "
            "NOT spilling to the metered API. Top up the pool or wait for the monthly "
            f"reset. exit={proc.returncode} stderr={(proc.stderr or '')[:300]}")
    return LLMUnavailable(
        f"claude CLI failed: exit={proc.returncode} stderr={(proc.stderr or '')[:300]}")


class ClaudeCliClient:
    provider = "claude-cli"

    def __init__(self, *, model: str | None = None, runner=None) -> None:
        self.model = model or DEFAULT_MODEL
        self._runner = runner or _default_runner

    def build_env(self) -> dict:
        return {k: v for k, v in os.environ.items() if k not in _STRIP_ENV}

    def build_argv(self) -> list[str]:
        return [CLI_BIN, "-p", "--output-format", "json",
                "--max-turns", "1", "--model", self.model]

    def build_prompt(self, *, system: str, messages: list[dict], schema: dict) -> str:
        user = "\n\n".join(m["content"] for m in messages if m.get("role") == "user")
        return (
            f"{system}\n\n{user}\n\n"
            "Respond with ONLY a single JSON object conforming to the JSON Schema "
            "below. No prose, no markdown fences, no explanation — just the JSON "
            f"object.\nJSON Schema:\n{json.dumps(schema)}"
        )

    def parse_stdout(self, events, *, schema: dict) -> ChatResponse:
        rate_limit = _find_event(events, "rate_limit_event")
        if rate_limit is not None:
            status = (rate_limit.get("rate_limit_info") or {}).get("status")
            if status not in (None, "allowed"):
                raise LLMConfigError(
                    f"claude CLI: rate_limit_info.status={status!r} (not 'allowed'). "
                    "NOT spilling to the metered API. Top up the pool or wait for the "
                    "monthly reset.")
        envelope = _find_event(events, "result")
        if envelope is None:
            raise LLMUnavailable("claude CLI output had no 'result' event")
        if envelope.get("is_error") or envelope.get("subtype") not in (None, "success"):
            raise LLMUnavailable(
                f"claude CLI returned error envelope: subtype={envelope.get('subtype')!r}")
        result = envelope.get("result")
        if not isinstance(result, str) or not result.strip():
            raise LLMUnavailable("claude CLI envelope had no 'result' text")
        inner = _extract_json(result)
        _require_keys(inner, schema)
        cost = envelope.get("total_cost_usd")
        if cost is not None:
            _log.info("claude-cli call: cost=$%.4f model=%s", cost, self.model)
        return ChatResponse(text=json.dumps(inner), provider=self.provider,
                            model=envelope.get("model", self.model),
                            finish_reason=envelope.get("subtype"),
                            usage=envelope.get("usage"))

    def complete_json(self, *, system: str, messages: list[dict], schema: dict,
                      max_tokens: int = 4096, temperature: float = 0.0,
                      timeout: float = 120.0, from_fixture: str | None = None) -> ChatResponse:
        # max_tokens / temperature are accepted for LLMClient parity; `claude -p`
        # does not expose them, so they are intentionally unused here.
        if from_fixture is not None:
            envelope = json.loads(Path(from_fixture).read_text(encoding="utf-8"))
            return self.parse_stdout(envelope, schema=schema)
        prompt = self.build_prompt(system=system, messages=messages, schema=schema)
        try:
            proc = self._runner(self.build_argv(), input=prompt,
                                env=self.build_env(), timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise LLMUnavailable(f"claude CLI timed out after {timeout}s") from e
        except FileNotFoundError as e:
            raise LLMConfigError(f"claude CLI not found ({CLI_BIN!r} not on PATH)") from e
        if proc.returncode != 0:
            raise _classify_failure(proc)
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise LLMUnavailable(
                f"claude CLI stdout was not JSON: {e}; stderr={(proc.stderr or '')[:300]}") from e
        return self.parse_stdout(envelope, schema=schema)

    def preflight(self) -> None:
        """Token-free readiness check: confirm the `claude` CLI is on PATH and runnable.
        Does NOT validate auth (that would spend the pool); a missing/auth-broken CLI
        surfaces on the first real call, fail-closed."""
        if shutil.which(CLI_BIN) is None:
            raise LLMConfigError(f"claude CLI not found: {CLI_BIN!r} not on PATH")
        try:
            proc = self._runner([CLI_BIN, "--version"], input="", env=self.build_env(), timeout=15)
        except Exception as e:
            raise LLMUnavailable(f"claude CLI --version failed: {e}") from e
        if proc.returncode != 0:
            raise LLMUnavailable(f"claude CLI --version exit={proc.returncode}")
