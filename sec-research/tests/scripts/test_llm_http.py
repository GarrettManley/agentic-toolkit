from __future__ import annotations
import json
import pytest


def test_post_json_from_fixture_opens_no_socket(tmp_path, monkeypatch):
    from llm import _http
    # Any real socket attempt must explode — fixture path must not reach it.
    monkeypatch.setattr(_http.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("socket opened")))
    fixture = tmp_path / "resp.json"
    fixture.write_text(json.dumps({"ok": True}), encoding="utf-8")
    out = _http.post_json("https://api.anthropic.com/v1/messages", {"x": 1},
                          bootstrap_hosts=frozenset({"api.anthropic.com"}),
                          from_fixture=str(fixture))
    assert out == {"ok": True}


def test_post_json_gates_before_socket(monkeypatch):
    from llm import _http
    from lib.policy import ScopeViolation
    calls = {}
    monkeypatch.setattr(_http, "check_http",
                        lambda url, **kw: calls.setdefault("gated", (url, kw)))
    monkeypatch.setattr(_http.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("would hit network")))
    with pytest.raises(AssertionError):  # gate passed (stub), socket stub raises
        _http.post_json("https://api.anthropic.com/v1/messages", {"x": 1},
                        bootstrap_hosts=frozenset({"api.anthropic.com"}))
    assert calls["gated"][0] == "https://api.anthropic.com/v1/messages"
    assert calls["gated"][1]["bootstrap_hosts"] == frozenset({"api.anthropic.com"})


def test_post_json_scope_violation_propagates(monkeypatch):
    from llm import _http
    from lib.policy import ScopeViolation
    def boom(url, **kw):
        raise ScopeViolation(url=url, host="evil.com", reason="not in scope")
    monkeypatch.setattr(_http, "check_http", boom)
    with pytest.raises(ScopeViolation):
        _http.post_json("https://evil.com/x", {}, bootstrap_hosts=frozenset())
