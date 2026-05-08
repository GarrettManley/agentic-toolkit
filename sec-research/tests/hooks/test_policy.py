"""Tests for hooks/lib/policy.py - subprocess HTTP scope enforcement."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def fresh_programs_dir(workspace_root, monkeypatch):
    """Inject the huntr-test fixture as the active programs dir for one test.

    Mirrors the pattern in test_pt1_scope.py.
    """
    from lib import paths, scope_match
    fixtures_dir = workspace_root / "tests" / "fixtures" / "huntr-test-program"
    test_programs = workspace_root / "programs-test-tmp"
    if test_programs.exists():
        shutil.rmtree(test_programs)
    test_programs.mkdir()
    target = test_programs / "huntr-test"
    shutil.copytree(fixtures_dir, target)
    monkeypatch.setattr(paths, "PROGRAMS_DIR", test_programs)
    monkeypatch.setattr(scope_match, "PROGRAMS_DIR", test_programs)
    scope_match.invalidate_scope_cache()
    yield test_programs
    shutil.rmtree(test_programs)
    scope_match.invalidate_scope_cache()


@pytest.fixture
def empty_programs_dir(workspace_root, monkeypatch, tmp_path):
    """No scopes loaded - simulates fresh-clone state for bootstrap tests."""
    from lib import paths, scope_match
    empty = tmp_path / "programs-empty"
    empty.mkdir()
    monkeypatch.setattr(paths, "PROGRAMS_DIR", empty)
    monkeypatch.setattr(scope_match, "PROGRAMS_DIR", empty)
    scope_match.invalidate_scope_cache()
    yield empty
    scope_match.invalidate_scope_cache()


@pytest.fixture
def isolated_ledger(tmp_path, monkeypatch):
    """Redirect ledger writes to a temp file so tests don't pollute submissions/ledger.jsonl."""
    from lib import ledger as ledger_mod
    fake_subs = tmp_path / "submissions"
    fake_subs.mkdir()
    fake_ledger = fake_subs / "ledger.jsonl"
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", fake_ledger)
    monkeypatch.setattr(ledger_mod, "SUBMISSIONS_DIR", fake_subs)
    yield fake_ledger


def _sign_test_override(workspace_root: Path, target: str, ttl_hours: int = 1) -> str:
    """Helper: invoke sign_override.py to create a signed PT-1 token. Returns token id."""
    cmd = [
        sys.executable,
        str(workspace_root / "scripts" / "sign_override.py"),
        "--rule", "PT-1",
        "--target", target,
        "--reason", "policy.py test fixture: exercise override-honor path of check_http",
        "--ttl-hours", str(ttl_hours),
        "--test-mode-confirm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    assert result.returncode == 0, f"sign_override failed: {result.stderr}"
    for line in result.stdout.splitlines():
        if "Token signed and written" in line:
            return Path(line.split(": ", 1)[1]).stem
    raise RuntimeError(f"could not find token id in: {result.stdout}")


def test_in_scope_url_returns_program_slug(fresh_programs_dir, isolated_ledger):
    from lib.policy import check_http
    ok, prog = check_http("https://registry.npmjs.org/fixture-pkg")
    assert ok is True
    assert prog == "huntr-test"


def test_out_of_scope_url_raises_scope_violation(fresh_programs_dir, isolated_ledger):
    from lib.policy import ScopeViolation, check_http
    with pytest.raises(ScopeViolation) as excinfo:
        check_http("https://random.example.com/path")
    assert excinfo.value.host == "random.example.com"
    assert excinfo.value.url == "https://random.example.com/path"
    assert excinfo.value.rule_id == "PT-1"


def test_bootstrap_host_allowed_without_scope(empty_programs_dir, isolated_ledger):
    from lib.policy import VENUE_BOOTSTRAP_HOSTS, check_http
    ok, prog = check_http("https://huntr.com/programs/abc", bootstrap_hosts=VENUE_BOOTSTRAP_HOSTS)
    assert ok is True
    assert prog is None  # bootstrap match returns slug=None


def test_bootstrap_dot_suffix_match(empty_programs_dir, isolated_ledger):
    from lib.policy import check_http
    # api.huntr.com should match an entry of "huntr.com" via dot-suffix.
    ok, prog = check_http("https://api.huntr.com/v1/programs", bootstrap_hosts={"huntr.com"})
    assert ok is True
    assert prog is None


def test_bootstrap_default_empty_blocks_venue(empty_programs_dir, isolated_ledger):
    from lib.policy import ScopeViolation, check_http
    # Default bootstrap_hosts=() means even huntr.com gets blocked when no scope loaded.
    with pytest.raises(ScopeViolation):
        check_http("https://huntr.com/x")


def test_signed_override_allows_blocked_host(
    override_key_setup, clean_overrides, fresh_programs_dir, isolated_ledger, workspace_root
):
    from lib.policy import check_http
    target = "evil.example"  # not in scope, not bootstrap
    _sign_test_override(workspace_root, target=target)
    ok, prog = check_http(f"https://{target}/path")
    assert ok is True
    assert prog is None  # override match returns slug=None
    # Token is single-use by default -> moved to overrides/used/
    used = list((workspace_root / "overrides" / "used").glob("*.json"))
    assert len(used) == 1


def test_expired_override_does_not_allow(
    override_key_setup, clean_overrides, fresh_programs_dir, isolated_ledger, workspace_root
):
    from lib import paths
    from lib.policy import ScopeViolation, check_http
    from lib.sign_verify import sign_token

    target = "evil.example"
    now = datetime.now(timezone.utc)
    payload = {
        "token_id": "ovr-test-expired",
        "rule_id": "PT-1",
        "scope": {"target": target},
        "max_uses": 1,
        "created_at": (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": "expired token for negative-path test of check_http override handling",
    }
    payload["signature"] = sign_token({k: v for k, v in payload.items()})
    paths.OVERRIDES_SIGNED_DIR.mkdir(parents=True, exist_ok=True)
    token_path = paths.OVERRIDES_SIGNED_DIR / f"{payload['token_id']}.json"
    token_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ScopeViolation):
        check_http(f"https://{target}/path")


def test_blocked_call_appends_policy_blocked_ledger_event(
    fresh_programs_dir, isolated_ledger, clean_overrides
):
    from lib.policy import ScopeViolation, check_http
    with pytest.raises(ScopeViolation):
        check_http("https://evil.invalid/path")
    assert isolated_ledger.exists()
    entries = [
        json.loads(line)
        for line in isolated_ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    blocked = [e for e in entries if e.get("event_type") == "policy-blocked"]
    assert len(blocked) == 1
    assert blocked[0]["url"] == "https://evil.invalid/path"
    assert blocked[0]["host"] == "evil.invalid"
    assert blocked[0]["rule_id"] == "PT-1"


def test_url_without_scheme_treated_as_host(empty_programs_dir, isolated_ledger):
    from lib.policy import check_http
    ok, prog = check_http("github.com/owner/repo", bootstrap_hosts={"github.com"})
    assert ok is True
    assert prog is None


def test_ledger_failure_does_not_suppress_block(
    fresh_programs_dir, isolated_ledger, clean_overrides, monkeypatch
):
    from lib import ledger as ledger_mod
    from lib.policy import ScopeViolation, check_http

    def boom(*args, **kwargs):
        raise OSError("ledger disk full (simulated)")

    monkeypatch.setattr(ledger_mod, "append_event", boom)
    # Should still raise ScopeViolation despite ledger.append_event raising.
    with pytest.raises(ScopeViolation):
        check_http("https://evil2.invalid/path")
