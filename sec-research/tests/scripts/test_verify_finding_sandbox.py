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
    poc_dir = tmp_path / "poc"
    poc_dir.mkdir()
    (poc_dir / "reproduce.sh").write_text("#!/bin/bash\necho ok\n")
    calls = {}
    def fake_sandbox_run(cmd, **kw):
        calls["cmd"] = cmd
        calls["kw"] = kw
        return _fake_result(exit_code=0)
    monkeypatch.setattr(vf, "sandbox_run", fake_sandbox_run)
    ok, msg = vf.run_poc_in_sandbox(
        workdir=poc_dir, ecosystem="npm", expected_exit_code=0,
        deterministic=False, expected_hash=None, timeout=60)
    assert ok is True
    # I2: pin exact cmd — must be ["bash", "reproduce.sh"], not ["bash", "poc/reproduce.sh"]
    assert calls["cmd"] == ["bash", "reproduce.sh"]
    # I2: workdir passed to sandbox_run must be the poc dir (not the whole finding dir)
    assert str(calls["kw"]["workdir_host"]).endswith("poc")


def test_verify_sandbox_error_fails_closed(tmp_path, monkeypatch):
    import verify_finding as vf
    from sandbox.runner import SandboxError
    poc_dir = tmp_path / "poc"
    poc_dir.mkdir()
    (poc_dir / "reproduce.sh").write_text("#!/bin/bash\necho ok\n")
    def boom(cmd, **kw):
        raise SandboxError("docker unreachable")
    monkeypatch.setattr(vf, "sandbox_run", boom)
    ok, msg = vf.run_poc_in_sandbox(workdir=poc_dir, ecosystem="npm",
                                    expected_exit_code=0, deterministic=False,
                                    expected_hash=None, timeout=60)
    assert ok is False and "sandbox" in msg.lower()  # no host fallback


def test_verify_deterministic_hash_mismatch_fails(tmp_path, monkeypatch):
    import verify_finding as vf
    poc_dir = tmp_path / "poc"
    poc_dir.mkdir()
    (poc_dir / "reproduce.sh").write_text("#!/bin/bash\necho DIFFERENT\n")
    monkeypatch.setattr(vf, "sandbox_run", lambda cmd, **kw: _fake_result(stdout="DIFFERENT\n"))
    ok, msg = vf.run_poc_in_sandbox(workdir=poc_dir, ecosystem="npm",
                                    expected_exit_code=0, deterministic=True,
                                    expected_hash="deadbeef", timeout=60)
    assert ok is False


def test_verify_timeout_fails(tmp_path, monkeypatch):
    import verify_finding as vf
    import hashlib
    from sandbox.runner import SandboxResult
    poc_dir = tmp_path / "poc"
    poc_dir.mkdir()
    (poc_dir / "reproduce.sh").write_text("#!/bin/bash\nsleep 999\n")
    monkeypatch.setattr(vf, "sandbox_run", lambda cmd, **kw: SandboxResult(
        exit_code=124, stdout="", stderr="timeout",
        stdout_sha256=hashlib.sha256(b"").hexdigest(), duration_s=1.0,
        timed_out=True, image="node:22-slim"))
    ok, msg = vf.run_poc_in_sandbox(workdir=poc_dir, ecosystem="npm",
                                    expected_exit_code=0, deterministic=False,
                                    expected_hash=None, timeout=1)
    assert ok is False and "tim" in msg.lower()


def test_verify_deterministic_without_hash_fails_clearly(tmp_path, monkeypatch):
    import verify_finding as vf
    poc_dir = tmp_path / "poc"
    poc_dir.mkdir()
    (poc_dir / "reproduce.sh").write_text("#!/bin/bash\necho ok\n")
    monkeypatch.setattr(vf, "sandbox_run", lambda cmd, **kw: _fake_result(exit_code=0))
    ok, msg = vf.run_poc_in_sandbox(workdir=poc_dir, ecosystem="npm",
                                    expected_exit_code=0, deterministic=True,
                                    expected_hash=None, timeout=60)
    assert ok is False and "expected_output_hash" in msg


def test_verify_missing_reproduce_sh_fails_before_sandbox(tmp_path, monkeypatch):
    """Pre-flight: if reproduce.sh is absent, return failure without launching a container."""
    import verify_finding as vf
    poc_dir = tmp_path / "poc"
    poc_dir.mkdir()
    # reproduce.sh intentionally NOT created
    launched = []
    monkeypatch.setattr(vf, "sandbox_run", lambda cmd, **kw: launched.append(cmd) or _fake_result())
    ok, msg = vf.run_poc_in_sandbox(workdir=poc_dir, ecosystem="npm",
                                    expected_exit_code=0, deterministic=False,
                                    expected_hash=None, timeout=60)
    assert ok is False
    assert "reproduce.sh" in msg
    assert launched == []  # sandbox never invoked
