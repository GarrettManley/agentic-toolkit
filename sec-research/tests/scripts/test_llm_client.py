from __future__ import annotations
import json
from pathlib import Path
import pytest

from verify.poc_prompt import POC_AUTHOR_SCHEMA

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "llm"


def test_select_client_default_is_claude(monkeypatch):
    monkeypatch.delenv("SECRESEARCH_LLM_PROVIDER", raising=False)
    from llm.client import select_client
    assert select_client().provider == "claude"


def test_select_client_env_override(monkeypatch):
    monkeypatch.setenv("SECRESEARCH_LLM_PROVIDER", "llama")
    from llm.client import select_client
    assert select_client().provider == "llama"


def test_select_client_arg_beats_env(monkeypatch):
    monkeypatch.setenv("SECRESEARCH_LLM_PROVIDER", "llama")
    from llm.client import select_client
    assert select_client("claude").provider == "claude"


def test_unknown_provider_raises():
    from llm.client import select_client, LLMConfigError
    with pytest.raises(LLMConfigError):
        select_client("gpt")


def test_claude_build_payload_uses_forced_tool():
    from llm.providers.claude import ClaudeApiClient
    c = ClaudeApiClient(api_key="sk-ant-test")
    schema = {"type": "object", "properties": {"hypotheses": {"type": "array"}}, "required": ["hypotheses"]}
    body = c.build_payload(system="sys", messages=[{"role": "user", "content": "hi"}],
                           schema=schema, max_tokens=2048, temperature=0.0)
    assert body["tool_choice"] == {"type": "tool", "name": "emit_hypotheses"}
    assert body["tools"][0]["name"] == "emit_hypotheses"
    assert body["tools"][0]["input_schema"] == schema
    assert body["system"] == "sys"


def test_claude_parse_response_extracts_tool_input():
    from llm.providers.claude import ClaudeApiClient
    raw = json.loads((FIX / "claude_messages_response.json").read_text("utf-8"))
    resp = ClaudeApiClient(api_key="sk-ant-test").parse_response(raw)
    assert resp.provider == "claude"
    payload = json.loads(resp.text)
    assert payload["hypotheses"][0]["target"]["identifier"] == "lodash"


def test_claude_complete_json_from_fixture():
    from llm.providers.claude import ClaudeApiClient
    resp = ClaudeApiClient(api_key="sk-ant-test").complete_json(
        system="s", messages=[{"role": "user", "content": "x"}],
        schema={"type": "object"}, from_fixture=str(FIX / "claude_messages_response.json"))
    assert json.loads(resp.text)["hypotheses"][0]["vuln_class"] == "dependency-cve"


def test_llama_build_payload_uses_response_format():
    from llm.providers.llama import LlamaServerClient
    schema = {"type": "object", "required": ["hypotheses"]}
    body = LlamaServerClient().build_payload(system="sys",
        messages=[{"role": "user", "content": "hi"}], schema=schema,
        max_tokens=2048, temperature=0.0)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] == schema
    assert body["messages"][0]["role"] == "system"
    assert body["temperature"] == 0.0


def test_llama_parse_response_reads_message_content():
    from llm.providers.llama import LlamaServerClient
    raw = json.loads((FIX / "llama_chat_response.json").read_text("utf-8"))
    resp = LlamaServerClient().parse_response(raw)
    assert resp.provider == "llama"
    assert json.loads(resp.text)["hypotheses"][0]["confidence"] == 0.6


def test_cli_build_env_strips_anthropic_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
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
    # "type": "result" is required so _find_event actually locates this as the
    # result event — omitting it would fail for the wrong reason ("no result
    # event found") instead of exercising _require_keys.
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMUnavailable
    bad = {"type": "result", "subtype": "success", "is_error": False, "result": '{"files": {}}'}
    with pytest.raises(LLMUnavailable):
        ClaudeCliClient().parse_stdout(bad, schema=POC_AUTHOR_SCHEMA)


def test_cli_parse_stdout_rejects_error_envelope():
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMUnavailable
    with pytest.raises(LLMUnavailable):
        ClaudeCliClient().parse_stdout({"type": "result", "is_error": True,
                                        "subtype": "error_max_turns", "result": ""},
                                       schema=POC_AUTHOR_SCHEMA)


def test_cli_parse_stdout_extracts_result_event_from_array():
    # Confirms array-unwrapping: a multi-event list (system/assistant/rate_limit_event/
    # result, mirroring the real claude -p shape found by Task 1's spike) is handled by
    # finding the LAST element with type=="result", ignoring the sibling events.
    from llm.providers.claude_cli import ClaudeCliClient
    events = [
        {"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
        {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}},
        {"type": "result", "subtype": "success", "is_error": False,
         "result": '{"files": {}, "trigger_cmd": ["x"], "sentinel_confirmed": "A", '
                   '"expected_confirmed_exit": 0, "sentinel_patched": "B", '
                   '"expected_patched_exit": 1, "reasoning": "r"}'},
    ]
    resp = ClaudeCliClient().parse_stdout(events, schema=POC_AUTHOR_SCHEMA)
    assert resp.provider == "claude-cli"


def test_cli_parse_stdout_raises_on_non_allowed_rate_limit():
    # Structured signal from Task 1's spike: a rate_limit_event with status != "allowed"
    # is a stronger pool-exhaustion signal than _classify_failure's keyword guessing, and
    # can in principle ride along an exit-0 envelope (never observed live — no quota was
    # burned to confirm — but checked proactively since it's cheap and additive).
    from llm.providers.claude_cli import ClaudeCliClient
    from llm.client import LLMConfigError
    events = [
        {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}},
        {"type": "result", "subtype": "success", "is_error": False,
         "result": '{"files": {}, "trigger_cmd": ["x"], "sentinel_confirmed": "A", '
                   '"expected_confirmed_exit": 0, "sentinel_patched": "B", '
                   '"expected_patched_exit": 1, "reasoning": "r"}'},
    ]
    with pytest.raises(LLMConfigError):
        ClaudeCliClient().parse_stdout(events, schema=POC_AUTHOR_SCHEMA)


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


def _ok_envelope_stdout():
    # Real claude -p stdout is a JSON ARRAY of session events (Task 1's spike finding) —
    # the result data is the LAST element with type=="result", not the whole stdout value.
    import json as _j
    return _j.dumps([
        {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}},
        {"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": 0.001,
         "result": _j.dumps({"files": {}, "trigger_cmd": ["x"],
                             "sentinel_confirmed": "A", "expected_confirmed_exit": 0,
                             "sentinel_patched": "B", "expected_patched_exit": 1,
                             "reasoning": "r"})},
    ])


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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake123")
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


def test_select_client_claude_cli_arg():
    from llm.client import select_client
    assert select_client("claude-cli").provider == "claude-cli"


def test_select_client_claude_cli_env(monkeypatch):
    monkeypatch.setenv("SECRESEARCH_LLM_PROVIDER", "claude-cli")
    from llm.client import select_client
    assert select_client().provider == "claude-cli"
