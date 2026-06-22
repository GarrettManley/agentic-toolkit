import subprocess
from pathlib import Path


class _FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


def test_clone_gates_then_runs_and_captures_sha(tmp_path, monkeypatch):
    from recon import clone as clonemod
    gated = {}
    monkeypatch.setattr(clonemod, "gate", lambda url: gated.setdefault("url", url))
    calls = []
    def runner(cmd, **kw):
        calls.append(cmd)
        if cmd[:2] == ["git", "clone"]:
            Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
            return _FakeProc()
        if "rev-parse" in cmd:
            return _FakeProc(stdout="abc123\n")
        return _FakeProc()
    r = clonemod.clone_repo("github.com/acme-org/acme", tmp_path, runner=runner)
    assert r.cloned is True and r.commit_sha == "abc123"
    assert r.clone_path.endswith("acme-org-acme")
    assert gated["url"] == "https://github.com/acme-org/acme"  # gate fired on the clone URL
    assert calls[0][:2] == ["git", "clone"]


def test_clone_failure_sets_skipped_reason(tmp_path, monkeypatch):
    from recon import clone as clonemod
    monkeypatch.setattr(clonemod, "gate", lambda url: None)
    def runner(cmd, **kw):
        if cmd[:2] == ["git", "clone"]:
            return _FakeProc(returncode=1)
        return _FakeProc()
    r = clonemod.clone_repo("github.com/acme-org/acme", tmp_path, runner=runner)
    assert r.cloned is False and r.skipped_reason and "clone" in r.skipped_reason.lower()


def test_clone_scope_violation_propagates(tmp_path, monkeypatch):
    from recon import clone as clonemod
    from lib.policy import ScopeViolation
    def boom(url):
        raise ScopeViolation(url=url, host="github.com", reason="test")
    monkeypatch.setattr(clonemod, "gate", boom)
    import pytest
    with pytest.raises(ScopeViolation):
        clonemod.clone_repo("github.com/acme-org/acme", tmp_path, runner=lambda *a, **k: _FakeProc())
