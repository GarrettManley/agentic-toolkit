import json
import pytest


@pytest.mark.parametrize("raw,expected", [
    ("acme-org/acme-pkg", "acme-org-acme-pkg"),
    ("Acme-Org/My_Pkg.js", "acme-org-my-pkg-js"),
    ("foo.", "foo"),
    ("@scope/pkg", "scope-pkg"),
    ("a__b", "a-b"),
    ("--trim--", "trim"),
])
def test_slugify(raw, expected):
    from fetchers._common import slugify
    assert slugify(raw) == expected


def test_utc_now_iso_shape():
    from fetchers._common import utc_now_iso
    s = utc_now_iso()
    assert s.endswith("Z") and "T" in s and len(s) == 20  # 2026-06-20T12:34:56Z


def test_http_get_from_fixture_skips_network(tmp_path):
    from fetchers import _http
    fx = tmp_path / "body.html"
    fx.write_text("<html>hi</html>", encoding="utf-8")
    assert _http.http_get("https://blocked.invalid", from_fixture=fx) == "<html>hi</html>"


def test_gh_api_json_from_fixture_parses(tmp_path):
    from fetchers import _http
    fx = tmp_path / "resp.json"
    fx.write_text(json.dumps({"full_name": "a/b"}), encoding="utf-8")
    assert _http.gh_api_json("/repos/a/b", from_fixture=fx) == {"full_name": "a/b"}


def test_http_get_live_path_calls_check_http(monkeypatch):
    """Live path must invoke the scope gate before opening a socket."""
    from fetchers import _http
    from lib.policy import ScopeViolation
    calls = {}

    def fake_check(url, *, bootstrap_hosts):
        calls["url"] = url
        raise ScopeViolation(url=url, host="huntr.com", reason="test")

    monkeypatch.setattr(_http, "check_http", fake_check)
    with pytest.raises(ScopeViolation):
        _http.http_get("https://huntr.com/repos/a/b")
    assert calls["url"] == "https://huntr.com/repos/a/b"
