import json
import pytest


def test_recon_infra_hosts_has_core_sources():
    from recon._hosts import RECON_INFRA_HOSTS
    for host in ("registry.npmjs.org", "pypi.org", "crates.io", "rubygems.org",
                 "api.github.com", "raw.githubusercontent.com", "github.com",
                 "services.nvd.nist.gov", "api.osv.dev"):
        assert host in RECON_INFRA_HOSTS


def test_http_get_from_fixture_skips_network(tmp_path):
    from recon import _http
    fx = tmp_path / "body.json"
    fx.write_text('{"ok":true}', encoding="utf-8")
    assert _http.http_get("https://blocked.invalid", from_fixture=fx) == '{"ok":true}'


def test_http_post_json_from_fixture_parses(tmp_path):
    from recon import _http
    fx = tmp_path / "resp.json"
    fx.write_text(json.dumps({"results": []}), encoding="utf-8")
    assert _http.http_post_json("https://blocked.invalid", {"queries": []}, from_fixture=fx) == {"results": []}


def test_gate_calls_check_http_with_recon_hosts(monkeypatch):
    from recon import _http
    from recon._hosts import RECON_INFRA_HOSTS
    seen = {}
    def fake_check(url, *, bootstrap_hosts):
        seen["url"] = url
        seen["hosts"] = bootstrap_hosts
    monkeypatch.setattr(_http, "check_http", fake_check)
    _http.gate("https://api.osv.dev/v1/querybatch")
    assert seen["url"] == "https://api.osv.dev/v1/querybatch"
    assert seen["hosts"] is RECON_INFRA_HOSTS


def test_http_get_live_path_gates_then_propagates_scope_violation(monkeypatch):
    from recon import _http
    from lib.policy import ScopeViolation
    def fake_check(url, *, bootstrap_hosts):
        raise ScopeViolation(url=url, host="evil.invalid", reason="test")
    monkeypatch.setattr(_http, "check_http", fake_check)
    with pytest.raises(ScopeViolation):
        _http.http_get("https://evil.invalid/x")  # live path: no fixture


def test_http_post_json_live_path_gates_then_propagates_scope_violation(monkeypatch):
    from recon import _http
    from lib.policy import ScopeViolation
    def fake_check(url, *, bootstrap_hosts):
        raise ScopeViolation(url=url, host="evil.invalid", reason="test")
    monkeypatch.setattr(_http, "check_http", fake_check)
    with pytest.raises(ScopeViolation):
        _http.http_post_json("https://evil.invalid/x", {})  # live path: no fixture
