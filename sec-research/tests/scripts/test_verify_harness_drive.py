"""Tests for verify.harness._drive_phased — two-phase install→trigger driver.

Offline only: uses an injected fake runner (no real docker).
Pattern copied from tests/scripts/test_sandbox_runner.py.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fake subprocess primitives (copied from test_sandbox_runner.py pattern)
# ---------------------------------------------------------------------------

class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _capture_runner(calls, *, returncode=0, stdout="", stderr=""):
    """Return a runner callable that appends (argv, kwargs) to ``calls``."""
    def runner(argv, **kw):
        calls.append((argv, kw))
        return _FakeCompleted(returncode=returncode, stdout=stdout, stderr=stderr)
    return runner


# ---------------------------------------------------------------------------
# Shared test fixture — minimal PocPlan that doesn't need TemplatedPocStrategy
# ---------------------------------------------------------------------------

def _make_plan():
    """Build a minimal PocPlan directly for harness tests.

    Kept independent of TemplatedPocStrategy so failures in the template
    don't cascade into drive tests.
    """
    from verify.strategy import PocPlan
    sentinel = "REDOS_CONFIRMED\n"
    sha = hashlib.sha256(sentinel.encode("utf-8")).hexdigest()
    return PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "minimatch@3.0.4"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256=sha,
        files={"trigger.js": "process.stdout.write('REDOS_CONFIRMED\\n'); process.exit(0);"},
        template_id="npm__minimatch__CVE-2022-3517",
    )


# ---------------------------------------------------------------------------
# Phase ordering + network mode
# ---------------------------------------------------------------------------

def test_install_runs_before_trigger_and_uses_bridge(tmp_path, monkeypatch):
    """First sandbox_run call uses --network bridge (install); second uses --network none (trigger)."""
    import verify.harness as h
    import sandbox.runner as r
    # Allow check_http to pass (registry host is whitelisted in bootstrap_hosts)
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    calls = []
    plan = _make_plan()
    h._drive_phased(plan, "hyp-001", "test-slug",
                    runner=_capture_runner(calls),
                    verdict_root=tmp_path)

    assert len(calls) == 2, f"expected 2 runner calls, got {len(calls)}"
    install_argv, trigger_argv = calls[0][0], calls[1][0]

    install_net = install_argv[install_argv.index("--network") + 1]
    trigger_net = trigger_argv[trigger_argv.index("--network") + 1]

    assert install_net == "bridge", f"install should use bridge, got {install_net!r}"
    assert trigger_net == "none", f"trigger should use none, got {trigger_net!r}"


# ---------------------------------------------------------------------------
# C2 — trigger is explicitly --network none
# ---------------------------------------------------------------------------

def test_trigger_network_none_explicit(tmp_path, monkeypatch):
    """C2: trigger must always run airgapped; assert the exact argv position."""
    import verify.harness as h
    import sandbox.runner as r
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    calls = []
    plan = _make_plan()
    h._drive_phased(plan, "hyp-c2", "slug-c2",
                    runner=_capture_runner(calls),
                    verdict_root=tmp_path)

    trigger_argv = calls[1][0]
    idx = trigger_argv.index("--network")
    assert trigger_argv[idx + 1] == "none"


# ---------------------------------------------------------------------------
# Shared workdir — install and trigger mount the same host path
# ---------------------------------------------------------------------------

def test_shared_workdir(tmp_path, monkeypatch):
    """Both phases receive the same host workdir path via the -v mount."""
    import verify.harness as h
    import sandbox.runner as r
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    calls = []
    plan = _make_plan()
    h._drive_phased(plan, "hyp-wd", "slug-wd",
                    runner=_capture_runner(calls),
                    verdict_root=tmp_path)

    def extract_workdir_mount(argv):
        # Find -v arg that mounts to :/work
        for i, arg in enumerate(argv):
            if arg == "-v" and ":/work" in argv[i + 1]:
                return argv[i + 1].split(":")[0]
        raise AssertionError(f"no :/work mount found in argv: {argv}")

    install_workdir = extract_workdir_mount(calls[0][0])
    trigger_workdir = extract_workdir_mount(calls[1][0])
    assert install_workdir == trigger_workdir, (
        f"install workdir {install_workdir!r} != trigger workdir {trigger_workdir!r}"
    )


# ---------------------------------------------------------------------------
# Files materialized before install
# ---------------------------------------------------------------------------

def test_files_materialized_before_install(tmp_path, monkeypatch):
    """plan.files are written to the workdir; trigger.js must exist after the call."""
    import verify.harness as h
    import sandbox.runner as r
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    calls = []
    plan = _make_plan()
    h._drive_phased(plan, "hyp-files", "slug-files",
                    runner=_capture_runner(calls),
                    verdict_root=tmp_path)

    # Reconstruct W from the verdict_root + slug + hypothesis_id
    W = tmp_path / "slug-files" / "work" / "hyp-files"
    assert (W / "trigger.js").exists(), "trigger.js was not materialized"
    content = (W / "trigger.js").read_text(encoding="utf-8")
    assert "REDOS_CONFIRMED" in content


# ---------------------------------------------------------------------------
# Install-failure short-circuit — exit != 0
# ---------------------------------------------------------------------------

def test_install_failure_raises_sandbox_error_and_trigger_not_called(tmp_path, monkeypatch):
    """If install exits non-zero, SandboxError is raised and trigger is never invoked."""
    import verify.harness as h
    import sandbox.runner as r
    from sandbox.runner import SandboxError
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    calls = []
    plan = _make_plan()
    with pytest.raises(SandboxError):
        h._drive_phased(plan, "hyp-fail", "slug-fail",
                        runner=_capture_runner(calls, returncode=1),
                        verdict_root=tmp_path)

    assert len(calls) == 1, (
        f"trigger must not run after install failure; got {len(calls)} calls"
    )


# ---------------------------------------------------------------------------
# Install-failure short-circuit — timed out
# ---------------------------------------------------------------------------

def test_install_timeout_raises_sandbox_error_and_trigger_not_called(tmp_path, monkeypatch):
    """If install times out, SandboxError is raised and trigger is never invoked."""
    import verify.harness as h
    import sandbox.runner as r
    from sandbox.runner import SandboxError
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    calls = []
    call_count = [0]

    def timeout_on_first(argv, **kw):
        call_count[0] += 1
        calls.append((argv, kw))
        if call_count[0] == 1:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=1)
        return _FakeCompleted(returncode=0)

    plan = _make_plan()
    with pytest.raises(SandboxError):
        h._drive_phased(plan, "hyp-timeout", "slug-timeout",
                        runner=timeout_on_first,
                        verdict_root=tmp_path)

    assert len(calls) == 1, (
        f"trigger must not run after install timeout; got {len(calls)} calls"
    )


# ---------------------------------------------------------------------------
# EvidenceCapture shape — success path
# ---------------------------------------------------------------------------

def test_evidence_capture_shape_on_success(tmp_path, monkeypatch):
    """On success, returned install_ev.phase=='install' and trigger_ev.phase=='trigger'."""
    import verify.harness as h
    import sandbox.runner as r
    from verify.model import EvidenceCapture
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    sentinel = "REDOS_CONFIRMED\n"
    calls = []
    plan = _make_plan()
    install_ev, trigger_ev = h._drive_phased(
        plan, "hyp-ev", "slug-ev",
        runner=_capture_runner(calls, returncode=0, stdout=sentinel),
        verdict_root=tmp_path,
    )

    assert isinstance(install_ev, EvidenceCapture)
    assert isinstance(trigger_ev, EvidenceCapture)
    assert install_ev.phase == "install"
    assert trigger_ev.phase == "trigger"

    # exit_code, timed_out, duration_s populated from SandboxResult
    assert install_ev.exit_code == 0
    assert trigger_ev.exit_code == 0
    assert install_ev.timed_out is False
    assert trigger_ev.timed_out is False

    # stdout_sha256 propagated correctly
    expected_sha = hashlib.sha256(sentinel.encode("utf-8")).hexdigest()
    assert trigger_ev.stdout_sha256 == expected_sha
    assert isinstance(trigger_ev.duration_s, float)
