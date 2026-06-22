import types
from pathlib import Path

import pytest


def _fake_result(exit_code=0, stdout="ok\n"):
    import hashlib
    from sandbox.runner import SandboxResult
    return SandboxResult(exit_code=exit_code, stdout=stdout, stderr="",
                         stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
                         duration_s=0.1, timed_out=False, image="node:22-slim")


def test_verify_runs_poc_via_sandbox(tmp_path, monkeypatch):
    import verify_finding as vf
    calls = {}
    def fake_sandbox_run(cmd, **kw):
        calls["cmd"] = cmd
        calls["kw"] = kw
        return _fake_result(exit_code=0)
    monkeypatch.setattr(vf, "sandbox_run", fake_sandbox_run)
    ok, msg = vf.run_poc_in_sandbox(  # see Step 3 for the exact helper name/shape
        poc_dir=tmp_path, ecosystem="npm", expected_exit_code=0,
        deterministic=False, expected_hash=None, timeout=60)
    assert ok is True
    assert "reproduce.sh" in " ".join(calls["cmd"])


def test_verify_sandbox_error_fails_closed(tmp_path, monkeypatch):
    import verify_finding as vf
    from sandbox.runner import SandboxError
    def boom(cmd, **kw):
        raise SandboxError("docker unreachable")
    monkeypatch.setattr(vf, "sandbox_run", boom)
    ok, msg = vf.run_poc_in_sandbox(poc_dir=tmp_path, ecosystem="npm",
                                    expected_exit_code=0, deterministic=False,
                                    expected_hash=None, timeout=60)
    assert ok is False and "sandbox" in msg.lower()  # no host fallback


def test_verify_deterministic_hash_mismatch_fails(tmp_path, monkeypatch):
    import verify_finding as vf
    monkeypatch.setattr(vf, "sandbox_run", lambda cmd, **kw: _fake_result(stdout="DIFFERENT\n"))
    ok, msg = vf.run_poc_in_sandbox(poc_dir=tmp_path, ecosystem="npm",
                                    expected_exit_code=0, deterministic=True,
                                    expected_hash="deadbeef", timeout=60)
    assert ok is False
