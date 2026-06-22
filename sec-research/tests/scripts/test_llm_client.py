from __future__ import annotations
import json
from pathlib import Path
import pytest

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
