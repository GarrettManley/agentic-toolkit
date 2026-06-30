# Claude-CLI LLM Provider → First Trustworthy sec-research Run (hb-322) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Plan-mode working copy:** this file. On execution, copy to the repo-canonical location `sec-research/docs/superpowers/plans/2026-06-30-hb-322-claude-cli-provider.md` (matches the existing `docs/superpowers/plans/` convention) and commit it sec-research-pure.

**Goal:** Add a `claude-cli` LLM provider that authors via the Claude Code CLI's subscription **programmatic credit pool** (not the metered API), then use it to drive hb-322's first trustworthy end-to-end run against huntr.com/minimatch.

**Why avoid the metered API (rationale, not just a label):** per hb-26v, the user explicitly declined routing LLM calls through the metered Anthropic API — metered, per-token billing with no pre-set ceiling was the named blocker, not raw cost magnitude. The credit pool is **billed at the same per-token API rates** (see Task 7 Step 2) — it is not a cheaper rate. The actual benefit is structural: it draws from a separate, finite, pre-allocated bucket that fails closed (CLI errors out) when exhausted, instead of risking unbounded metered spend with no built-in stop. That bounded-allowance property — not cost — is why this plan builds a CLI-shelling provider instead of just using the existing, already-tested `claude` (metered) provider for hb-322's first run.

**Architecture:** A new `ClaudeCliClient` implements the existing `LLMClient` Protocol by shelling out to `claude -p --output-format json` through an injectable `runner`. It owns two responsibilities the HTTP adapters get for free: stripping `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` from the subprocess env (so the CLI uses the credit pool, never metered billing), and hardening the model's JSON (the CLI envelope wraps un-grammar-constrained text). It is selected by `select_client("claude-cli")` and picked up automatically by `LLMPocStrategy` and `llm/generate.py`, which both route through `select_client()`. Part 2 runs the supervised pipeline through it.

**Why build full reusable infrastructure for one run (value/effort):** Tasks 1-4 build a fully wired, reusable provider (`select_client`-integrated, tested) even though Task 6 spends it on a single one-off run. This is intentional, not gold-plating: Task 7 Step 2 files the deferred follow-up (`SECRESEARCH_POC_LLM_PROVIDER` hybrid routing — local hypothesis-gen + `claude-cli` PoC-authoring) that will reuse this exact client in the nightly loop. Building it as a first-class `select_client()` provider now, rather than a throwaway script, is what makes that follow-up a small diff instead of a rewrite.

**Tech Stack:** Python 3.14, stdlib only (`subprocess`, `json`, `re`, `shutil`, `logging`), pytest. No new dependencies. The `claude` CLI must be on PATH and authed to a subscription session.

## Global Constraints

- **Provider name string:** `"claude-cli"` (verbatim — used in `select_client`, `ChatResponse.provider`, and tests).
- **Env hygiene (load-bearing):** the subprocess env MUST omit `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`. Test-asserted. If present, the CLI silently routes to metered API billing — defeating the purpose.
- **Fail-closed:** any CLI failure (non-zero exit, error envelope, exhausted credit pool) raises (`LLMConfigError` for config/pool, `LLMUnavailable` for transient). NEVER fall back to the metered API.
- **Model floor:** default model `sonnet` (overridable via `SECRESEARCH_CLAUDE_CLI_MODEL`). Do NOT default below sonnet — haiku/local-7B reproduce the hb-26v non-discriminating-PoC failure.
- **`.text`-is-valid-JSON invariant:** `complete_json` must return `ChatResponse.text` as a JSON string whose object contains every key in `schema["required"]` — the harness does not cushion malformed/partial JSON (`llm_strategy.py:78`).
- **Interface compatibility:** `complete_json` accepts `max_tokens`/`temperature`/`timeout`/`from_fixture` for signature parity; `claude -p` does not expose `temperature`/`max_tokens`, so those are accepted-but-unused (document inline).
- **sec-research commit hygiene:** stage only `sec-research/` paths per commit (keeps the workspace verify-gate skip, `check_verify_before_commit.py:147-156`). Conventional-commit headers, capitalized summary, ≤72 chars. Keep install-verb substrings (`npm install`, `pip install`, `cargo install`, `Stop-Process`, `bash …reproduce.sh`) OUT of commit messages (PT-5 string-matches them). `Trace-ID:` trailer is only needed if `findings/**` is staged (G-4) — none of Part 1 stages findings.
- **Run all tests with:** `pytest` from inside `sec-research/`.

---

## File Structure

- `scripts/llm/providers/claude_cli.py` — **new.** The `ClaudeCliClient` adapter + module helpers `_extract_json`, `_require_keys`, `_classify_failure`, `_default_runner`. One responsibility: drive `claude -p` and return schema-valid JSON or fail closed.
- `scripts/llm/client.py` — **modify** (`select_client`, lines 46-54): one `if name == "claude-cli":` branch + updated error string.
- `tests/scripts/test_llm_client.py` — **modify:** add the `claude-cli` unit tests alongside the existing claude/llama ones.
- `tests/fixtures/llm/claude_cli_response.json` — **new:** a realistic success envelope (raw `result`).
- `tests/fixtures/llm/claude_cli_response_fenced.json` — **new:** same, but `result` wrapped in a ```json fence (proves fence-stripping).

(No bespoke live-smoke file is added — see the cut Task 5 note below; the existing `tests/scripts/test_llm_live.py::test_live_hypothesis_roundtrip` is reused unmodified for live proof.)

---

## Task 0: Commit the plan to its repo-canonical location

The plan-mode working copy lives outside the repo. Per the header note, version it before execution begins.

- [ ] **Step 1: Copy and commit** (run from the Workspace root, where `sec-research/` is a subdirectory — hence the `sec-research/` path prefix here, unlike Task 6's commit, which runs with `sec-research/` already as cwd):
```bash
cp "C:/Users/Garre/.claude/plans/the-next-highest-value-pure-kettle.md" \
   sec-research/docs/superpowers/plans/2026-06-30-hb-322-claude-cli-provider.md
git add sec-research/docs/superpowers/plans/2026-06-30-hb-322-claude-cli-provider.md
git commit -m "docs(sec-research): Add hb-322 claude-cli provider implementation plan"
```

---

## Task 1: CLI contract spike + fixtures

Confirm the real `claude -p --output-format json` envelope shape and credit-pool behavior empirically, and freeze it into fixtures the adapter is built against. (Not red-green — a verification spike whose deliverable is two fixtures + a confirmed contract.)

**Gating note (load-bearing):** the code shown in Task 2 Step 3 is a *template*, written against this plan's best-available assumption of the envelope shape. It is gated on this task's actual findings — see Step 7 below, which is a hard checkpoint before Task 2 begins.

**Files:**
- Create: `tests/fixtures/llm/claude_cli_response.json`, `tests/fixtures/llm/claude_cli_response_fenced.json`

- [ ] **Step 1: Smoke the CLI headless JSON contract**

Run (PowerShell, from `sec-research/`, with the API key cleared so we observe the subscription/credit-pool path):
```powershell
Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue
'Respond with ONLY this JSON object: {"ok": true}' | claude -p --output-format json --max-turns 1 --model sonnet
```
Expected: a single JSON envelope on stdout with at least `subtype`/`is_error`/`result`/`total_cost_usd` fields, where `result` is the model's text containing `{"ok": true}` (possibly fenced). Note the exact field names (`result`, `subtype`, `is_error`, `total_cost_usd`, `usage`, `model`).

- [ ] **Step 2: Smoke against the real nested schema shape (not just the trivial baseline)**

Step 1 only proves the CLI can echo a flat 1-key object. The adapter's actual payload is `POC_AUTHOR_SCHEMA` (`verify/poc_prompt.py:14`) — a nested object with a `files` map and a `trigger_cmd` array. Reliability on a flat object does not establish reliability on a nested one. Run a second smoke with a prompt that demands that shape, e.g.:
```powershell
'Respond with ONLY this JSON object (no prose, no fences): {"files": {"a.txt": "hi"}, "trigger_cmd": ["node", "a.txt"], "sentinel_confirmed": "X", "expected_confirmed_exit": 0, "sentinel_patched": "Y", "expected_patched_exit": 1, "reasoning": "test"}' | claude -p --output-format json --max-turns 1 --model sonnet
```
Expected: `result` parses as valid JSON with all 7 keys intact, including the nested `files` object and `trigger_cmd` array (no truncation, no flattening). If the CLI degrades the nested shape (truncates, drops keys, or wraps differently than the flat case), record that — it changes `_extract_json`'s robustness requirements before Task 2 is written.

- [ ] **Step 3: Confirm the credit-pool / fail-closed behavior is observable (best-effort — do not burn quota to force exhaustion)**

There is no safe, low-cost way to deliberately exhaust the operator's real credit pool just to observe its error text, so this step is **best-effort and unverified against a real pool-exhausted response**: check the CLI's `--help` output and any documented pool-exhaustion behavior, and record whatever is found. `_classify_failure`'s keyword set (`credit`/`quota`/`usage limit`/`rate limit`/`exhaust`) is therefore a best-effort guess at the real error text, not a confirmed match. Task 6 Step 4 (the first real run) is the actual validation point — if a pool-exhaustion error occurs there and isn't classified as `LLMConfigError`, widen the keyword set then.

- [ ] **Step 4: Write the success fixture** `tests/fixtures/llm/claude_cli_response.json`

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "num_turns": 1,
  "model": "claude-sonnet-4-6",
  "result": "{\"files\": {\"trigger.js\": \"const m = require('minimatch'); try { m('', 'a'.repeat(1e5)+'!(('); process.stdout.write('VULN_CONFIRMED\\n'); process.exit(0);} catch(e){ process.stdout.write('PATCHED_OK\\n'); process.exit(0);} \"}, \"trigger_cmd\": [\"node\", \"trigger.js\"], \"sentinel_confirmed\": \"VULN_CONFIRMED\", \"expected_confirmed_exit\": 0, \"sentinel_patched\": \"PATCHED_OK\", \"expected_patched_exit\": 0, \"reasoning\": \"Differential ReDoS trigger; affected version hangs/throws, fixed version returns cleanly.\"}",
  "total_cost_usd": 0.0042,
  "session_id": "spike-fixture",
  "usage": {"input_tokens": 220, "output_tokens": 140}
}
```

- [ ] **Step 5: Write the fenced fixture** `tests/fixtures/llm/claude_cli_response_fenced.json`

Same envelope, but `result` wrapped in a fence to prove stripping. Set `result` to exactly:
```json
{
  "subtype": "success",
  "is_error": false,
  "result": "```json\n{\"files\": {\"trigger.js\": \"x\"}, \"trigger_cmd\": [\"node\", \"trigger.js\"], \"sentinel_confirmed\": \"A\", \"expected_confirmed_exit\": 0, \"sentinel_patched\": \"B\", \"expected_patched_exit\": 1, \"reasoning\": \"r\"}\n```",
  "total_cost_usd": 0.001
}
```

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/llm/claude_cli_response.json tests/fixtures/llm/claude_cli_response_fenced.json
git commit -m "test(sec-research): Add claude-cli envelope fixtures from contract spike"
```

- [ ] **Step 7: Checkpoint — confirm before starting Task 2**

Before writing any code in Task 2, compare Steps 1-2's actual recorded output against this plan's assumptions:
- Do the real envelope field names match `result`/`subtype`/`is_error`/`total_cost_usd`?
- Did Step 2's nested-schema smoke come back intact (no truncation/flattening)?
- Does Step 3's best-effort pool-exhaustion text (if any was found) overlap with `_POOL_TOKENS = ("credit", "quota", "usage limit", "rate limit", "exhaust")`?

If any answer is "no," edit Task 2 Step 3's code block (the field-access paths in `parse_stdout`, the `_POOL_TOKENS` tuple, and/or `_extract_json`'s robustness) to match reality **before** typing it in — the code shown there is a template against this plan's best-available assumption, not a guaranteed-correct final implementation. Do not commit it verbatim if the spike contradicts it.

---

## Task 2: `ClaudeCliClient` pure core (env hygiene, argv, prompt, parse)

The no-I/O seams: `build_env`, `build_argv`, `build_prompt`, `parse_stdout`, and helpers. Fully unit-testable without the real binary.

**Files:**
- Create: `scripts/llm/providers/claude_cli.py`
- Test: `tests/scripts/test_llm_client.py`

**Interfaces:**
- Consumes: `from llm.client import ChatResponse, LLMConfigError, LLMUnavailable` (`client.py:14-28`); `POC_AUTHOR_SCHEMA` (`verify/poc_prompt.py:14`) in tests.
- Produces: `class ClaudeCliClient` with `provider = "claude-cli"`, `__init__(self, *, model=None, runner=None)`, methods `build_env() -> dict`, `build_argv() -> list[str]`, `build_prompt(*, system, messages, schema) -> str`, `parse_stdout(envelope: dict, *, schema: dict) -> ChatResponse`. Task 3 adds `complete_json` and `preflight`.

- [ ] **Step 1: Write failing tests** (append to `tests/scripts/test_llm_client.py`; add `from verify.poc_prompt import POC_AUTHOR_SCHEMA` near the top imports — the `FIX` fixture-path constant used below is already defined at the top of this file, `FIX = Path(__file__).resolve().parents[1] / "fixtures" / "llm"`; no new definition needed)

```python
def test_cli_build_env_strips_anthropic_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
    monkeypatch.setenv("CLI_ENV_MARKER", "keepme")
    from llm.providers.claude_cli import ClaudeCliClient
    env = ClaudeCliClient().build_env()
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert env.get("CLI_ENV_MARKER") == "keepme"


def test_cli_build_argv_headless_json_single_turn():
    from llm.providers.claude_cli import ClaudeCliClient
    argv = ClaudeCliClient(model="sonnet").build_argv()
    assert argv[0:2] == ["claude", "-p"]
    assert argv[argv.index("--output-format") + 1] == "json"
    assert argv[argv.index("--max-turns") + 1] == "1"
    assert argv[argv.index("--model") + 1] == "sonnet"


def test_cli_build_prompt_embeds_system_user_and_schema():
    from llm.providers.claude_cli import ClaudeCliClient
    p = ClaudeCliClient().build_prompt(system="SYS", messages=[{"role": "user", "content": "DOIT"}],
                                       schema={"type": "object", "required": ["files"]})
    assert "SYS" in p and "DOIT" in p
    assert "ONLY" in p and '"required"' in p  # schema serialized + JSON-only instruction


def test_cli_parse_stdout_extracts_inner_json():
    import json
    from llm.providers.claude_cli import ClaudeCliClient
    env = json.loads((FIX / "claude_cli_response.json").read_text("utf-8"))
    resp = ClaudeCliClient().parse_stdout(env, schema=POC_AUTHOR_SCHEMA)
    assert resp.provider == "claude-cli"
    assert json.loads(resp.text)["sentinel_confirmed"] == "VULN_CONFIRMED"


def test_cli_parse_stdout_strips_markdown_fences():
    import json
    from llm.providers.claude_cli import ClaudeCliClient
    env = json.loads((FIX / "claude_cli_response_fenced.json").read_text("utf-8"))
    resp = ClaudeCliClient().parse_stdout(env, schema=POC_AUTHOR_SCHEMA)
    assert json.loads(resp.text)["trigger_cmd"] == ["node", "trigger.js"]


def test_cli_parse_stdout_rejects_missing_required_keys():
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMUnavailable
    bad = {"subtype": "success", "result": '{"files": {}}'}
    with pytest.raises(LLMUnavailable):
        ClaudeCliClient().parse_stdout(bad, schema=POC_AUTHOR_SCHEMA)


def test_cli_parse_stdout_rejects_error_envelope():
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMUnavailable
    with pytest.raises(LLMUnavailable):
        ClaudeCliClient().parse_stdout({"is_error": True, "subtype": "error_max_turns",
                                        "result": ""}, schema=POC_AUTHOR_SCHEMA)


def test_cli_default_runner_resolves_binary_via_which(monkeypatch):
    # `claude` is very likely an npm .cmd/.ps1 shim on Windows; subprocess.run(["claude", ...],
    # shell=False) raises FileNotFoundError for shim binaries unless resolved via shutil.which
    # (which honors PATHEXT). This asserts the runner does that resolution, not build_argv —
    # build_argv still returns the bare "claude" name (see test_cli_build_argv_... above).
    import subprocess
    from llm.providers import claude_cli
    seen = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setattr(claude_cli.shutil, "which", lambda name: r"C:\resolved\claude.cmd")
    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)
    claude_cli._default_runner(["claude", "-p"], input="x", env={}, timeout=5)
    assert seen["argv"][0] == r"C:\resolved\claude.cmd"
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/scripts/test_llm_client.py -k cli -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'llm.providers.claude_cli'`.

- [ ] **Step 3: Implement the pure core** in `scripts/llm/providers/claude_cli.py`

```python
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

    def parse_stdout(self, envelope: dict, *, schema: dict) -> ChatResponse:
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/scripts/test_llm_client.py -k cli -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/llm/providers/claude_cli.py tests/scripts/test_llm_client.py
git commit -m "feat(sec-research): Add claude-cli provider pure core with env hygiene + JSON hardening"
```

---

## Task 3: `complete_json` orchestration + `preflight` (subprocess, fixture, fail-closed)

The live path: run the subprocess (or replay a fixture), map failures fail-closed, and a token-free `preflight`.

**Files:**
- Modify: `scripts/llm/providers/claude_cli.py`
- Test: `tests/scripts/test_llm_client.py`

**Interfaces:**
- Produces: `complete_json(self, *, system, messages, schema, max_tokens=4096, temperature=0.0, timeout=120.0, from_fixture=None) -> ChatResponse` and `preflight(self) -> None`, matching the `LLMClient` Protocol (`client.py:35-43`). The injectable `runner(argv, *, input, env, timeout) -> subprocess.CompletedProcess` is the test seam.

- [ ] **Step 1: Write failing tests** (append to `tests/scripts/test_llm_client.py`)

```python
def _ok_envelope_stdout():
    import json as _j
    return _j.dumps({"subtype": "success", "is_error": False, "total_cost_usd": 0.001,
                     "result": _j.dumps({"files": {}, "trigger_cmd": ["x"],
                                         "sentinel_confirmed": "A", "expected_confirmed_exit": 0,
                                         "sentinel_patched": "B", "expected_patched_exit": 1,
                                         "reasoning": "r"})})


def test_cli_complete_json_from_fixture():
    import json
    from llm.providers.claude_cli import ClaudeCliClient
    resp = ClaudeCliClient().complete_json(
        system="s", messages=[{"role": "user", "content": "x"}],
        schema=POC_AUTHOR_SCHEMA, from_fixture=str(FIX / "claude_cli_response.json"))
    assert resp.provider == "claude-cli"
    assert json.loads(resp.text)["expected_patched_exit"] == 0


def test_cli_complete_json_subprocess_omits_key_and_pipes_prompt(monkeypatch):
    import subprocess
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
    seen = {}

    def fake(argv, *, input, env, timeout):
        seen["env"], seen["input"], seen["argv"] = env, input, argv
        return subprocess.CompletedProcess(argv, 0, stdout=_ok_envelope_stdout(), stderr="")

    from llm.providers.claude_cli import ClaudeCliClient
    resp = ClaudeCliClient(runner=fake).complete_json(
        system="SYS", messages=[{"role": "user", "content": "HELLO"}], schema=POC_AUTHOR_SCHEMA)
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert "HELLO" in seen["input"] and "SYS" in seen["input"]
    assert resp.provider == "claude-cli"


def test_cli_complete_json_pool_exhausted_fails_closed():
    import subprocess
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMConfigError

    def fake(argv, *, input, env, timeout):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Credit balance is too low")

    with pytest.raises(LLMConfigError):
        ClaudeCliClient(runner=fake).complete_json(
            system="s", messages=[{"role": "user", "content": "x"}], schema=POC_AUTHOR_SCHEMA)


def test_cli_complete_json_transient_failure_is_unavailable():
    import subprocess
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMUnavailable

    def fake(argv, *, input, env, timeout):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="network error")

    with pytest.raises(LLMUnavailable):
        ClaudeCliClient(runner=fake).complete_json(
            system="s", messages=[{"role": "user", "content": "x"}], schema=POC_AUTHOR_SCHEMA)


def test_cli_preflight_raises_when_binary_missing(monkeypatch):
    from llm.providers import claude_cli
    from llm.client import LLMConfigError
    monkeypatch.setattr(claude_cli.shutil, "which", lambda _: None)
    with pytest.raises(LLMConfigError):
        claude_cli.ClaudeCliClient().preflight()


def test_cli_preflight_passes_when_version_ok(monkeypatch):
    import subprocess
    from llm.providers import claude_cli
    monkeypatch.setattr(claude_cli.shutil, "which", lambda _: "/usr/bin/claude")
    ok = lambda argv, *, input, env, timeout: subprocess.CompletedProcess(argv, 0, "2.0.0", "")
    claude_cli.ClaudeCliClient(runner=ok).preflight()  # no raise
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/scripts/test_llm_client.py -k "cli_complete or cli_preflight" -v`
Expected: FAIL — `AttributeError: 'ClaudeCliClient' object has no attribute 'complete_json'`.

- [ ] **Step 3: Implement** `complete_json` + `preflight` (append the two methods to `class ClaudeCliClient`)

```python
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/scripts/test_llm_client.py -k cli -v`
Expected: PASS (all `cli` tests, 14).

- [ ] **Step 5: Commit**

```bash
git add scripts/llm/providers/claude_cli.py tests/scripts/test_llm_client.py
git commit -m "feat(sec-research): Add claude-cli complete_json + token-free preflight, fail-closed"
```

**Known accepted risk (not fixed in this plan):** `verify_hypotheses` (`harness.py:316-325`) only catches `SeedIncomplete`/`SandboxError` per-hypothesis during the verify stage. `LLMUnavailable`/`LLMConfigError` raised by `ClaudeCliClient.complete_json()` — e.g. on a malformed claude-cli JSON response while authoring a PoC — are NOT caught per-item there; they propagate uncaught and abort the *entire* Task 6 run on the first bad hypothesis, instead of degrading to a per-item SKIPPED/ERROR verdict like every other failure mode in that loop. Fixing this would mean editing `verify_hypotheses` itself, which is outside this plan's File Structure (`harness.py` is not listed as a file this plan modifies). Accepted as a known risk for hb-322's first run: if it fires, Task 6 Step 4 aborts mid-run, and the operator must inspect which hypothesis/response triggered it (via stdout / the partial journal) before re-running.

---

## Task 4: Wire `claude-cli` into `select_client()`

**Files:**
- Modify: `scripts/llm/client.py:46-54`
- Test: `tests/scripts/test_llm_client.py`

**Interfaces:**
- Consumes: `ClaudeCliClient` (Task 2/3). Produces: `select_client("claude-cli")` returns it; `SECRESEARCH_LLM_PROVIDER=claude-cli` selects it.

- [ ] **Step 1: Write failing tests**

```python
def test_select_client_claude_cli_arg():
    from llm.client import select_client
    assert select_client("claude-cli").provider == "claude-cli"


def test_select_client_claude_cli_env(monkeypatch):
    monkeypatch.setenv("SECRESEARCH_LLM_PROVIDER", "claude-cli")
    from llm.client import select_client
    assert select_client().provider == "claude-cli"
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/scripts/test_llm_client.py -k claude_cli -v`
Expected: FAIL — `LLMConfigError: unknown LLM provider 'claude-cli'`.

- [ ] **Step 3: Implement** — add the branch in `select_client` (after the `llama` branch, before the `raise`):

```python
    if name == "claude-cli":
        from llm.providers.claude_cli import ClaudeCliClient
        return ClaudeCliClient()
```

And update the error string to:
```python
    raise LLMConfigError(f"unknown LLM provider {name!r} (expected 'claude', 'claude-cli', or 'llama')")
```

- [ ] **Step 4: Run the full suite**

Run: `pytest`
Expected: PASS — all prior tests (~416) plus the new `claude-cli` tests green. (`test_unknown_provider_raises` still passes — `"gpt"` is still unknown.)

- [ ] **Step 5: Commit**

```bash
git add scripts/llm/client.py tests/scripts/test_llm_client.py
git commit -m "feat(sec-research): Select claude-cli provider via env and factory arg"
```

---

## Task 5 — Cut (scope-cutter finding)

Originally a bespoke gated live smoke test (`tests/scripts/test_llm_live.py`, a new `test_claude_cli_live_returns_schema_valid_json`). **Cut**: it duplicates the existing `test_live_hypothesis_roundtrip` in the same file, which already honors `SECRESEARCH_LLM_PROVIDER` via `select_client()` and is gated the same way (`@pytest.mark.skipif(os.environ.get("LLM_LIVE") != "1", ...)`). Running that existing test with `SECRESEARCH_LLM_PROVIDER=claude-cli` set is a strict superset of the bespoke version — it exercises the real `wrapper_schema(load_schema())` hypothesis shape against real recon fixture data, not a toy `{"ok": true}` schema. No new file or step is needed; the "Live proof" verification criterion below repoints at this existing test.

---

## Task 6: Execute hb-322 — first trustworthy supervised run

Operational, not TDD. Drive the real pipeline through `claude-cli` against minimatch and capture a trustworthy, journaled outcome. Run from inside `sec-research/`.

**Deliverable:** a `RunJournal` under `runtime/journals/` plus a short outcome note at `docs/superpowers/research/2026-06-30-hb-322-first-real-run.md` recording the terminal state (finding draft / known-CVE dedup / defensible null) and the evidence for it.

- [ ] **Step 1: Fail-closed run shell + preflight.** In PowerShell from `sec-research/`:
```powershell
Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue   # any accidental metered path now fails loud
Remove-Item Env:\ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue
$env:SECRESEARCH_LLM_PROVIDER = "claude-cli"
$env:SECRESEARCH_POC_STRATEGY = "llm"
gh auth status
python scripts/init_workspace.py --verify
```
Expected: `gh auth status` shows an authed account (Step 2's `fetch_program.py --venue huntr` and the verify stage's ecosystem inference in `fetchers/_common.py` both shell out to `gh api`; an unauthed/missing `gh` silently degrades to the underspecified hb-7hf scope fallback — catch it here instead). `init_workspace.py --verify` reports OK, but note its Docker/sandbox check is **warn-only** — it can report "healthy" even when Docker is actually unreachable. It does NOT positively confirm Docker reachability; the real fail-closed gate is `nightly.py`'s own `_preflight()` (`sandbox_doctor()`), which only fires inside Step 3/4 below. Treat Step 1 as a cheap sanity check, not a Docker guarantee.

**Critical — Steps 1-4 MUST run in one continuous PowerShell session, not as separate tool invocations.** `nightly.py` has no `--poc-strategy` CLI flag; `SECRESEARCH_POC_STRATEGY` (set above) is a bare env var read by `select_strategy()` (`scripts/verify/strategy.py`) at call time inside Step 4. A subagent or execution harness that opens a fresh shell per checkbox loses this env var silently — `select_strategy()` then falls back to `'templated'` with no error, and Task 6's entire point (exercising `claude-cli` in the verify stage) never happens. If your execution harness cannot guarantee one continuous session, re-export both `$env:SECRESEARCH_LLM_PROVIDER` and `$env:SECRESEARCH_POC_STRATEGY` immediately before Steps 3 and 4, and verify with `echo $env:SECRESEARCH_POC_STRATEGY` (must print `llm`, not empty) before proceeding each time.

- [ ] **Step 2: Load the program scope (step zero — `nightly.py` exits 2 with no scope).**
```powershell
python scripts/fetch_program.py --venue huntr --identifier isaacs/minimatch
```
Expected: a `programs/<slug>/scope.yaml` (or `scope.draft.yaml`) written, with an npm `package` asset carrying an ecosystem (so the dependency-cve playbook is hypothesis-eligible). Re-run safety: `fetch_program.py` is self-protecting against duplicate writes — it raises `FileExistsError` and refuses to overwrite an already-written `scope.yaml` unless `--force` is passed, so retrying this step after a partial later-stage failure is safe (don't pass `--force` unless intentionally re-fetching). If only a `repo` asset resolves (no `package`/ecosystem), fall back per `hb-7hf`: hand-author a scope YAML following the canonical example in `docs/SCOPE_SCHEMA.md` (a `program_slug`/`venue`/`in_scope` with at least one `asset_type: package` entry carrying an `ecosystem: npm`), save it anywhere under the repo (e.g. `programs/isaacs-minimatch.scope.yaml`), and load it with `python scripts/load_program.py --from-file <path>` (or scaffold one first via `python scripts/load_program.py --scaffold --venue huntr --slug isaacs-minimatch` and fill in the placeholders) — acceptance criterion: `lib/schema_validate.validate_program` passes (`load_program.py` calls it; a non-zero exit means the hand-authored YAML is invalid). Verify: `ls programs/`.

- [ ] **Step 3: Dry run to hypothesize — prove the provider bridge reaches the first LLM-touching stage.**
```powershell
python scripts/nightly.py --supervised --provider claude-cli --until hypothesize
```
`--until recon` would not work here: `stage_recon` makes no LLM call at all, so the success check below (`claude-cli call: cost=$…`) would be unreachable at that stage. `--until hypothesize` runs recon then hypothesis generation (`stage_hypothesize` → `generate_hypotheses` → `select_client().complete_json()`), the first stage that actually calls `claude-cli`. Expected: preflight passes (provider + `sandbox_doctor` — this is where Docker reachability is actually confirmed, per Step 1's caveat), recon and hypothesize complete, no metered call. **Critical check:** confirm the hypothesize-stage subprocess inherits `SECRESEARCH_LLM_PROVIDER=claude-cli` and `SECRESEARCH_POC_STRATEGY=llm` — because we exported both as real env vars (Step 1) and cleared `ANTHROPIC_API_KEY`, any accidental fallback to the metered `claude` provider raises `LLMConfigError` instead of billing. A `claude-cli call: cost=$…` log line confirms the bridge works. The verify stage's own bridge (the second LLM-touching stage, where `claude-cli` authors PoC code) is confirmed for real in Step 4 — there's no safe dry-run for it that doesn't also spend the pool.

- [ ] **Step 4: Positive preconditions, then the full supervised run, non-interactive.**

Immediately before spending real pool credit, confirm — don't assume — the env is what Step 1 intended:
```powershell
$env:ANTHROPIC_API_KEY   # must print nothing (empty) — confirms the key is actually absent, not just "removed earlier in this session"
claude --version          # must succeed — confirms the CLI itself is present and runnable
claude -p "say ok" --output-format json --max-turns 1   # one trivial authed call — confirms the CLI is authed to a subscription session (a one-time low-cost spend, not a dry run)
```
Then the real run:
```powershell
python scripts/nightly.py --supervised --provider claude-cli --yes
```
`--yes` is required: this command runs from a non-interactive shell tool call, and `_pause_for_inspection` (`nightly.py:264-272`) calls `input()`, which EOF-aborts the run at the very first checkpoint without it. `--yes` skips the interactive halts but still writes a checkpoint to the run journal at each stage (`nightly.py:303-305`), so inspection happens **post-hoc** by reading `runtime/journals/<run>.json` after the run finishes (Step 5), not via live halts. Drive recon → hypothesize → verify (differential PoC in the Docker sandbox) → triage/dedup → draft. Watch for: hypotheses generated (non-zero), the verify stage authoring a PoC via `claude-cli` and the differential oracle returning a **real verdict** (VERIFIED or a discriminating REFUTED) — **not** SKIPPED.

**Spend ceiling (manual, since `nightly.py` has no built-in cap):** there is no CLI flag or code-level cap on hypothesis count or total spend. Before running, use Task 1's per-call cost observation (~$0.001-$0.01/call) and the recon item count from Step 3's dry run to form a rough expected ceiling (e.g. recon items × playbooks-per-item × ~2 calls/hypothesis). If the run prints `cost=$…` lines well past that estimate with no terminal stage reached, Ctrl-C it (see the interrupt contract immediately below) rather than letting it run unbounded.

**Interrupt/resume contract (what's left behind if this is killed mid-run, and how to recover):** `nightly.py --supervised` has no resume primitive — `RunJournal` only records `checkpoint()` entries for stages already *reached*, and `finish()` is only called on a normal/aborted-via-halt exit, never on a hard kill. If the process is killed mid-stage: (1) the journal under `runtime/journals/` will show the last `reached` checkpoint but no `finish` entry — that's your last-known-good marker; (2) Docker containers are launched with `--rm` (`sandbox/runner.py:72`), so they self-clean on their own exit, but a container mid-trigger when the parent is killed may linger until its own internal timeout — check `wsl -e docker ps` and remove manually (`wsl -e docker rm -f <id>`) if one is still running after a few minutes; (3) `findings/` is only written at the draft stage (Stage 6) — if killed before then, nothing partial lands there. Recovery: there is no partial-resume — re-running Step 4 from scratch re-executes every stage, including hypothesize and verify, which **re-spends credit-pool cost** for any LLM calls that already ran. Confirm via the journal which stage was reached before deciding whether a clean re-run is worth the re-spend.

- [ ] **Step 5: Capture and document the outcome.** Read the latest `runtime/journals/<run>.json`. Write `docs/superpowers/research/2026-06-30-hb-322-first-real-run.md` recording which trustworthy terminal state was reached and its evidence: (a) a draft finding under `findings/<trace>/` (PoC + evidence + Tier-1 `Citation:`), (b) correct known-CVE dedup at triage, or (c) a defensible evidence-backed null with the full hypothesis audit trail. Note total credit-pool spend (sum of the logged `cost=$…` lines).

- [ ] **Step 6: Commit the outcome note** (sec-research-pure; cwd is `sec-research/`, so no path prefix):
```bash
git add docs/superpowers/research/2026-06-30-hb-322-first-real-run.md
git commit -m "docs(sec-research): Record hb-322 first real supervised run outcome"
```
**If outcome (a) occurred** (a draft finding under `findings/<trace>/`), that directory must also be committed — it is not covered by the command above. Stage it separately, with the `Trace-ID:` trailer G-4 requires whenever `findings/**` is staged:
```bash
git add findings/<trace>/
git commit -m "docs(sec-research): Draft hb-322 finding <trace>

Trace-ID: <trace>"
```

**Re-run semantics (risk, undefined by the underlying scripts):** neither `fetch_program.py`'s nor `nightly.py`'s re-run behavior after a *partial* failure is guarded beyond what Step 2's `FileExistsError` protection and Step 4's interrupt contract above describe. A second full `nightly.py --supervised --yes` run over the same loaded scope will re-generate and re-verify hypotheses from scratch (no de-dup against a prior run's journal), risking duplicate credit-pool spend and, if Stage 6 is reached twice, a duplicate finding draft for the same novel hypothesis (`draft_findings` allocates a fresh trace-id per call — it does not check for an existing draft of the same hypothesis). Don't re-run Step 4 casually; consult the journal first.

---

## Task 7: Close out — bead, follow-up, retrospective

- [ ] **Step 1: Close hb-322** (only if Task 6 reached a trustworthy outcome — a draft finding, a correctly-deduped known-CVE, or a defensible evidence-backed null):
```bash
bd -C C:/Users/Garre/.claude/harness-backlog close hb-322
```
**If Task 6's outcome is ambiguous or partial** (e.g. it aborted mid-run via the interrupt contract above, or reached a terminal state but without confidence it's trustworthy) — do NOT close hb-322. Instead leave it open, append a comment recording exactly what state was reached and why it isn't trustworthy yet (`bd -C C:/Users/Garre/.claude/harness-backlog comment hb-322 "<what happened, what's unresolved>"`), and treat re-attempting Task 6 (after addressing the gap) as the next step rather than closing prematurely.

- [ ] **Step 2: File the deferred hybrid-routing follow-up** with the cost rationale, passing the body via `-d`/`--description` so it's actually attached to the created issue (not just left in this plan's prose):
```bash
bd -C C:/Users/Garre/.claude/harness-backlog create "sec-research: per-PoC-strategy provider override (local hypothesis-gen + claude-cli PoC) to conserve the programmatic credit pool in the nightly loop" -p 3 -t task -d "hb-26v 'local-seed + Claude-PoC' verdict, now with a concrete cost reason: claude -p draws a finite monthly credit-pool at the same per-token API rates (not a cheaper rate), so running hypothesis-gen locally and spending the pool only on the PoC step conserves it. Scope: ~30 lines + tests — a SECRESEARCH_POC_LLM_PROVIDER override that select_strategy() threads into LLMPocStrategy(client=select_client(<override>))."
```

- [ ] **Step 3: Retrospective.** Run `retrospective:plan-retrospective` (delivery lifecycle does this). Capture: did the JSON hardening hold against real `claude -p` output; did env-stripping keep usage on the credit pool (check the `cost=$…` logs vs. any out-of-pocket); what the first real verify verdict was; any `--provider` / `POC_STRATEGY` bridge surprises in `nightly.py`.

---

## Verification (end-to-end)

- **Unit:** `pytest tests/scripts/test_llm_client.py -k cli -v` → all `claude-cli` tests green; `pytest` → full suite (~416 + new) green.
- **Env hygiene (the load-bearing claim):** `test_cli_complete_json_subprocess_omits_key_and_pipes_prompt` asserts `ANTHROPIC_API_KEY` is absent from the subprocess env even when set in the parent.
- **Fail-closed:** `test_cli_complete_json_pool_exhausted_fails_closed` asserts an exhausted pool raises `LLMConfigError` (no metered spill).
- **Live proof:** with `ANTHROPIC_API_KEY` unset and `SECRESEARCH_LLM_PROVIDER=claude-cli` set, `LLM_LIVE=1 pytest tests/scripts/test_llm_live.py -k live_hypothesis_roundtrip -v` (the existing test, reused per the cut Task 5 — see above) returns a schema-valid hypothesis payload, emitting a `cost=$…` log line (credit-pool path confirmed).
- **hb-322:** the supervised `nightly.py` run reaches a journaled terminal state where the verify stage emits a real verdict (not SKIPPED) on ≥1 hypothesis, and the outcome note documents a trustworthy result.

## Self-Review notes

- **Coverage:** provider build (Tasks 1-4) + run (Task 6) + closeout (Task 7) cover both halves of the goal. The "minimal now, defer hybrid" decision is honored — no per-strategy routing built (filed as Task 7 Step 2 follow-up instead).
- **Type consistency:** `ClaudeCliClient.provider == "claude-cli"` used identically in adapter, `select_client`, and every test; `parse_stdout(envelope, *, schema)` signature matches all call sites; `ChatResponse(text, provider, model, finish_reason, usage)` matches `client.py:22-28`.
- **No placeholders:** every code/test step shows complete code; the only deliberately empirical step is Task 1 (spike to confirm the real CLI envelope field names before locking `parse_stdout`).

## Retrospective

_To be completed after execution via `retrospective:plan-retrospective` (see Task 7 Step 3)._
