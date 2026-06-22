import json
import subprocess
from pathlib import Path

import pytest


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _capture_runner(calls, *, returncode=0, stdout="ok\n", stderr=""):
    def runner(argv, **kw):
        calls.append((argv, kw))
        return _FakeCompleted(returncode=returncode, stdout=stdout, stderr=stderr)
    return runner


def test_execute_phase_builds_hardened_no_network_argv(tmp_path):
    from sandbox.runner import sandbox_run
    calls = []
    res = sandbox_run(["bash", "poc/reproduce.sh"], ecosystem="npm", phase="execute",
                      workdir_host=tmp_path, timeout=30, runner=_capture_runner(calls))
    argv = calls[0][0]
    assert argv[:4] == ["wsl", "-e", "docker", "run"]
    assert "--rm" in argv
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    assert "--cap-drop" in argv and argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges" in argv
    assert "--memory" in argv and "--cpus" in argv and "--pids-limit" in argv
    assert "node:22-slim" in argv
    assert argv[-2:] == ["bash", "poc/reproduce.sh"]
    assert res.image == "node:22-slim" and res.exit_code == 0
    assert res.stdout_sha256 == __import__("hashlib").sha256(b"ok\n").hexdigest()


def test_install_phase_uses_bridge_and_gates_registry(tmp_path, monkeypatch):
    import sandbox.runner as r
    gated = []
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: gated.append((url, bootstrap_hosts)))
    calls = []
    sandbox_run = r.sandbox_run
    sandbox_run(["npm", "install", "left-pad@1.3.0"], ecosystem="npm", phase="install",
                workdir_host=tmp_path, timeout=60, runner=_capture_runner(calls))
    argv = calls[0][0]
    assert argv[argv.index("--network") + 1] == "bridge"
    assert "npm_config_ignore_scripts=true" in " ".join(argv)  # safe-install env injected
    # registry host gated before the run
    assert gated and "registry.npmjs.org" in gated[0][0]


def test_install_gate_scope_violation_propagates(tmp_path, monkeypatch):
    import sandbox.runner as r
    from lib.policy import ScopeViolation
    runner_calls = []
    def boom(url, *, bootstrap_hosts):
        raise ScopeViolation(url=url, host="evil.invalid", reason="test")
    monkeypatch.setattr(r, "check_http", boom)
    with pytest.raises(ScopeViolation):
        r.sandbox_run(["curl", "x"], ecosystem="npm", phase="install",
                      workdir_host=tmp_path, timeout=10, network_allow=["evil.invalid"],
                      runner=_capture_runner(runner_calls))
    assert runner_calls == []


def test_source_mounted_read_only(tmp_path):
    from sandbox.runner import sandbox_run
    calls = []
    src = tmp_path / "src"; src.mkdir()
    sandbox_run(["true"], ecosystem="npm", phase="execute", workdir_host=tmp_path,
                source_host=src, timeout=10, runner=_capture_runner(calls))
    joined = " ".join(calls[0][0])
    assert ":/src:ro" in joined


def test_unknown_ecosystem_raises_sandbox_error(tmp_path):
    from sandbox.runner import sandbox_run, SandboxError
    with pytest.raises(SandboxError):
        sandbox_run(["true"], ecosystem="maven", phase="execute",
                    workdir_host=tmp_path, timeout=10, runner=lambda *a, **k: _FakeCompleted())


def test_timeout_sets_timed_out(tmp_path):
    from sandbox.runner import sandbox_run
    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kw.get("timeout", 1))
    res = sandbox_run(["sleep", "999"], ecosystem="npm", phase="execute",
                      workdir_host=tmp_path, timeout=1, runner=runner)
    assert res.timed_out is True and res.exit_code == 124


def test_docker_unreachable_raises_sandbox_error(tmp_path):
    from sandbox.runner import sandbox_run, SandboxError
    def runner(argv, **kw):
        raise FileNotFoundError("wsl not found")
    with pytest.raises(SandboxError):
        sandbox_run(["true"], ecosystem="npm", phase="execute",
                    workdir_host=tmp_path, timeout=10, runner=runner)


def test_run_appends_ledger_event(tmp_path, monkeypatch):
    import sandbox.runner as r
    ledger = tmp_path / "submissions" / "ledger.jsonl"
    monkeypatch.setattr(r, "LEDGER_PATH", ledger)
    r.sandbox_run(["true"], ecosystem="npm", phase="execute", workdir_host=tmp_path,
                  timeout=10, runner=lambda argv, **k: __import__("types").SimpleNamespace(
                      returncode=0, stdout="", stderr=""))
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    evt = json.loads(lines[-1])
    assert evt["event"] == "sandbox-exec" and evt["image"] == "node:22-slim"
    assert evt["phase"] == "execute" and evt["exit"] == 0


def test_execute_phase_does_not_gate_network(tmp_path, monkeypatch):
    import sandbox.runner as r
    gated = []
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: gated.append(url))
    calls = []
    r.sandbox_run(["true"], ecosystem="npm", phase="execute",
                  workdir_host=tmp_path, timeout=10, runner=_capture_runner(calls))
    assert gated == []


def test_empty_network_allow_raises(tmp_path, monkeypatch):
    import sandbox.runner as r
    from sandbox.runner import SandboxError
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)
    with pytest.raises(SandboxError):
        r.sandbox_run(["npm", "install", "x"], ecosystem="npm", phase="install",
                      workdir_host=tmp_path, timeout=10, network_allow=[],
                      runner=lambda *a, **k: _FakeCompleted())


def test_invalid_phase_raises(tmp_path):
    from sandbox.runner import sandbox_run, SandboxError
    with pytest.raises(SandboxError):
        sandbox_run(["true"], ecosystem="npm", phase="excute",
                    workdir_host=tmp_path, timeout=10,
                    runner=lambda *a, **k: _FakeCompleted())


def test_non_windows_mount_path_raises(tmp_path):
    from sandbox.runner import sandbox_run, SandboxError
    with pytest.raises(SandboxError):
        sandbox_run(["true"], ecosystem="npm", phase="execute",
                    workdir_host=Path("/etc"), timeout=10,
                    runner=lambda *a, **k: _FakeCompleted())


def _docker_available():
    import subprocess
    try:
        p = subprocess.run(["wsl", "-e", "docker", "info"], capture_output=True, text=True, timeout=20)
        return p.returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(not _docker_available(), reason="docker engine not reachable in WSL2")
def test_integration_real_container_echo(tmp_path):
    from sandbox.runner import sandbox_run
    res = sandbox_run(["printf", "hello"], ecosystem="npm", phase="execute",
                      workdir_host=tmp_path, timeout=60)
    assert res.exit_code == 0 and "hello" in res.stdout
