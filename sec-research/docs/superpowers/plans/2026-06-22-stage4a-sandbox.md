# Stage 4a — Guarded Sandboxed Subprocess Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `scripts/sandbox/` package so risky subprocesses (registry installs, PoC `reproduce.sh`) execute inside a host-isolated Docker container (via `wsl -e docker`) through one audited, scope-gated chokepoint, and rewire `verify_finding.py` off its uncontained `subprocess.run`.

**Architecture:** A `sandbox_run()` chokepoint constructs a hardened `wsl -e docker run` invocation (cap-drop, resource limits, read-only source mount, `--network none` for execute / gated bridge for install), runs it through an injectable `runner` (so tests touch no docker/wsl), returns a structured `SandboxResult`, and appends a `sandbox-exec` audit event to the ledger. `sandbox_doctor()` verifies docker reachability fail-closed. `verify_finding.py` calls `sandbox_run` and keeps its existing exit-code + stdout-hash determinism checks.

**Tech Stack:** Python 3.14, `wsl -e docker` (docker engine inside WSL2), stdlib only (`subprocess`, `hashlib`, `json`, `pathlib`, `dataclasses`), `pytest`. All unit tests are offline via an injected `runner`; one integration smoke is docker-gated and auto-skips.

**Tracking:** `hb-wy4` (Follows up hb-ahp). Spec: `docs/superpowers/specs/2026-06-22-stage4a-sandbox-design.md` (trace-20260622-001).

## Global Constraints

- **Working directory:** all commands run from inside `sec-research/`. Commits stage **only** `sec-research/` paths.
- **Stage 1 is the contract:** do NOT modify `schema/*.json`, `hooks/policy.py`, or any hook. New `scripts/sandbox/` package + new tests are additive. The ONLY existing files modified are `scripts/verify_finding.py` (the PoC-runner rewire) and `scripts/init_workspace.py` (optional doctor hook).
- **No uncontained path survives (C1):** when docker is unreachable, `sandbox_run` raises `SandboxError`; it NEVER falls back to direct host execution. `verify_finding` surfaces the error rather than running the PoC on the host.
- **Container hardening (every run):** `--rm`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--memory 512m`, `--cpus 1.0`, `--pids-limit 256`, host workdir mounted at `/work` (`-w /work`), cloned source (if any) mounted read-only at `/src:ro`, wall-clock timeout that kills the container.
- **Phase→network:** `phase="execute"` → `--network none`; `phase="install"` → `--network bridge` + per-ecosystem safe-install env + each `network_allow` host gated via `policy.check_http(...)` BEFORE the run.
- **`ScopeViolation` propagates uncaught** from `sandbox_run` (it carries the ledger side-effect); docker/runtime failures raise `SandboxError`.
- **Audit:** every run appends a best-effort `sandbox-exec` JSON line to `submissions/ledger.jsonl` (never suppresses the result/raise).
- **WSL2 path translation:** Windows host paths → `/mnt/c/...` for `-v` mounts.
- **Pinned values:** images `node:22-slim` / `python:3.12-slim` / `rust:1-slim` / `ruby:3.3-slim`; limits as above.
- **TDD, frequent commits, DRY, YAGNI.** Run `pytest` before every commit. Baseline at plan start: 116 tests.

---

## File Structure

**Create:**
- `scripts/sandbox/__init__.py` — package marker (empty).
- `scripts/sandbox/_wslpath.py` — `win_to_wsl(path) -> str` (pure).
- `scripts/sandbox/_images.py` — `ECOSYSTEMS`, `image_for`, `registry_for`, `safe_install_env`, `REGISTRY_HOSTS`, `UnknownEcosystem` (pure).
- `scripts/sandbox/runner.py` — `sandbox_run`, `SandboxResult`, `SandboxError` + ledger append. The chokepoint.
- `scripts/sandbox/doctor.py` — `sandbox_doctor`, CLI `main`.
- `tests/scripts/test_sandbox_wslpath.py`, `test_sandbox_images.py`, `test_sandbox_runner.py`, `test_sandbox_doctor.py`, `test_verify_finding_sandbox.py`.

**Modify:**
- `scripts/verify_finding.py` — replace the direct `subprocess.run(reproduce.sh)` with `sandbox_run`.
- `scripts/init_workspace.py` — call `sandbox_doctor` under `--verify` (warn-only; does not hard-fail workspace init).

**Available from conftest (Stage 2):** `tests/conftest.py` puts `scripts/` and `hooks/` on `sys.path`, so `from sandbox.runner import sandbox_run` and `from lib.policy import check_http, ScopeViolation` resolve in tests. If `from sandbox...` raises `ModuleNotFoundError`, add `scripts/` to the conftest inserts (do not duplicate).

---

## Task 1: Pure helpers — `_wslpath.py` + `_images.py`

**Files:**
- Create: `scripts/sandbox/__init__.py` (empty)
- Create: `scripts/sandbox/_wslpath.py`
- Create: `scripts/sandbox/_images.py`
- Create: `tests/scripts/test_sandbox_wslpath.py`, `tests/scripts/test_sandbox_images.py`

**Interfaces:**
- Produces: `win_to_wsl(path: Path | str) -> str`. `ECOSYSTEMS: dict[str, dict]`. `image_for(ecosystem: str) -> str` (raises `UnknownEcosystem`). `registry_for(ecosystem: str) -> str`. `safe_install_env(ecosystem: str) -> list[str]` (docker `-e` flag pairs). `REGISTRY_HOSTS: frozenset[str]`. `UnknownEcosystem(ValueError)`.
- Consumes: nothing.

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_sandbox_wslpath.py`:

```python
from pathlib import Path
import pytest


def test_win_to_wsl_c_drive():
    from sandbox._wslpath import win_to_wsl
    assert win_to_wsl(r"C:\Users\Garre\Workspace\sec-research") == "/mnt/c/Users/Garre/Workspace/sec-research"


def test_win_to_wsl_lowercases_drive():
    from sandbox._wslpath import win_to_wsl
    assert win_to_wsl(r"D:\data\x") == "/mnt/d/data/x"


def test_win_to_wsl_accepts_path_object():
    from sandbox._wslpath import win_to_wsl
    out = win_to_wsl(Path("C:/Users/Garre/x"))
    assert out == "/mnt/c/Users/Garre/x"
```

`tests/scripts/test_sandbox_images.py`:

```python
import pytest


def test_image_for_known_ecosystems():
    from sandbox._images import image_for
    assert image_for("npm") == "node:22-slim"
    assert image_for("pypi") == "python:3.12-slim"
    assert image_for("cargo") == "rust:1-slim"
    assert image_for("rubygems") == "ruby:3.3-slim"


def test_image_for_unknown_raises():
    from sandbox._images import image_for, UnknownEcosystem
    with pytest.raises(UnknownEcosystem):
        image_for("maven")


def test_registry_for_and_hosts():
    from sandbox._images import registry_for, REGISTRY_HOSTS
    assert registry_for("npm") == "registry.npmjs.org"
    assert "pypi.org" in REGISTRY_HOSTS and "crates.io" in REGISTRY_HOSTS


def test_safe_install_env_npm_disables_scripts():
    from sandbox._images import safe_install_env
    env = safe_install_env("npm")
    # env is a flat list of docker -e flag pairs
    assert "-e" in env and any("ignore_scripts=true" in e for e in env)


def test_safe_install_env_unknown_is_empty():
    from sandbox._images import safe_install_env
    assert safe_install_env("cargo") == []  # cargo has no global script-disable in v1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_sandbox_wslpath.py tests/scripts/test_sandbox_images.py -v`
Expected: FAIL (`No module named 'sandbox'`).

- [ ] **Step 3: Implement `__init__.py` + `_wslpath.py`**

`scripts/sandbox/__init__.py`: empty file.

`scripts/sandbox/_wslpath.py`:

```python
"""Translate a Windows host path to the /mnt/<drive>/... form WSL2 docker mounts expect."""
from __future__ import annotations

import re
from pathlib import Path

_DRIVE_RE = re.compile(r"^([A-Za-z]):/(.*)$")


def win_to_wsl(path: Path | str) -> str:
    s = str(path).replace("\\", "/")  # normalize separators first
    m = _DRIVE_RE.match(s)
    if not m:
        return s  # already POSIX-ish; pass through
    drive, rest = m.group(1).lower(), m.group(2)
    return f"/mnt/{drive}/{rest}"
```

- [ ] **Step 4: Implement `_images.py`**

```python
"""Per-ecosystem sandbox image, registry host, and safe-install env.

REGISTRY_HOSTS is the install-phase allow-set passed to policy.check_http.
safe_install_env returns docker `-e` flag pairs that neutralize install-time
script execution where the ecosystem supports a global switch (npm). Others rely
on host-isolation in v1 (a proxy-allowlist + per-ecosystem hardening is a follow-up)."""
from __future__ import annotations


class UnknownEcosystem(ValueError):
    """Ecosystem has no configured sandbox image."""


ECOSYSTEMS: dict[str, dict] = {
    "npm": {"image": "node:22-slim", "registry": "registry.npmjs.org",
            "install_env": {"npm_config_ignore_scripts": "true"}},
    "pypi": {"image": "python:3.12-slim", "registry": "pypi.org", "install_env": {}},
    "cargo": {"image": "rust:1-slim", "registry": "crates.io", "install_env": {}},
    "rubygems": {"image": "ruby:3.3-slim", "registry": "rubygems.org", "install_env": {}},
}

REGISTRY_HOSTS: frozenset[str] = frozenset(v["registry"] for v in ECOSYSTEMS.values())


def _entry(ecosystem: str) -> dict:
    try:
        return ECOSYSTEMS[ecosystem]
    except KeyError:
        raise UnknownEcosystem(f"no sandbox image for ecosystem {ecosystem!r}")


def image_for(ecosystem: str) -> str:
    return _entry(ecosystem)["image"]


def registry_for(ecosystem: str) -> str:
    return _entry(ecosystem)["registry"]


def safe_install_env(ecosystem: str) -> list[str]:
    """Flat list of docker -e flag pairs, e.g. ['-e', 'npm_config_ignore_scripts=true']."""
    out: list[str] = []
    for k, v in _entry(ecosystem).get("install_env", {}).items():
        out += ["-e", f"{k}={v}"]
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_sandbox_wslpath.py tests/scripts/test_sandbox_images.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/sandbox/__init__.py scripts/sandbox/_wslpath.py scripts/sandbox/_images.py tests/scripts/test_sandbox_wslpath.py tests/scripts/test_sandbox_images.py
git commit -m "feat(sandbox): wsl path translation + per-ecosystem image/registry map"
```

---

## Task 2: The chokepoint — `runner.py`

**Files:**
- Create: `scripts/sandbox/runner.py`
- Create: `tests/scripts/test_sandbox_runner.py`

**Interfaces:**
- Produces: `SandboxResult(exit_code: int, stdout: str, stderr: str, stdout_sha256: str, duration_s: float, timed_out: bool, image: str)` (frozen). `SandboxError(RuntimeError)`. `sandbox_run(cmd: list[str], *, ecosystem: str, phase: str = "execute", workdir_host, timeout: float, network_allow: list[str] | None = None, source_host=None, runner=subprocess.run, clock=time.monotonic) -> SandboxResult`.
- Consumes: `lib.policy.check_http`, `lib.policy.ScopeViolation`, `lib.paths.WORKSPACE_ROOT`, `sandbox._images.{image_for, registry_for, safe_install_env, REGISTRY_HOSTS, UnknownEcosystem}`, `sandbox._wslpath.win_to_wsl`.

> Ledger note: read `hooks/lib/policy.py` to see how it appends a `policy-blocked` event to `submissions/ledger.jsonl`; reuse that helper if one is exported. Otherwise use the self-contained `_append_ledger` below (best-effort JSON line to `WORKSPACE_ROOT/submissions/ledger.jsonl`).

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_sandbox_runner.py`:

```python
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
    def boom(url, *, bootstrap_hosts):
        raise ScopeViolation(url=url, host="evil.invalid", reason="test")
    monkeypatch.setattr(r, "check_http", boom)
    with pytest.raises(ScopeViolation):
        r.sandbox_run(["curl", "x"], ecosystem="npm", phase="install",
                      workdir_host=tmp_path, timeout=10, network_allow=["evil.invalid"],
                      runner=lambda *a, **k: _FakeCompleted())


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
    assert res.timed_out is True and res.exit_code != 0


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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_sandbox_runner.py -v`
Expected: FAIL (`No module named 'sandbox.runner'`).

- [ ] **Step 3: Implement `runner.py`**

```python
"""Guarded sandboxed subprocess execution — the single chokepoint for risky commands.

Every risky subprocess (registry install, PoC reproduce.sh) runs inside a hardened
`wsl -e docker run` container: cap-drop, resource limits, read-only source mount,
--network none (execute) or gated bridge (install). check_http gates declared
install hosts BEFORE the run (ScopeViolation propagates uncaught). Docker/runtime
failures raise SandboxError — there is NO direct-host fallback. Every run appends a
best-effort sandbox-exec event to the ledger. The runner is injectable for offline tests."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from lib.policy import check_http
from lib.paths import WORKSPACE_ROOT
from sandbox._images import (REGISTRY_HOSTS, UnknownEcosystem, image_for,
                             registry_for, safe_install_env)
from sandbox._wslpath import win_to_wsl

LEDGER_PATH = WORKSPACE_ROOT / "submissions" / "ledger.jsonl"

MEM_LIMIT = "512m"
CPU_LIMIT = "1.0"
PIDS_LIMIT = "256"


class SandboxError(RuntimeError):
    """Docker/runtime failure: daemon unreachable, missing image, bad invocation, timeout-kill."""


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    stdout_sha256: str
    duration_s: float
    timed_out: bool
    image: str


def _append_ledger(event: dict) -> None:
    try:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        pass  # best-effort; never suppress the result/raise


def _build_argv(image, cmd, *, network, workdir_host, source_host, extra_env) -> list[str]:
    argv = ["wsl", "-e", "docker", "run", "--rm",
            "--memory", MEM_LIMIT, "--cpus", CPU_LIMIT, "--pids-limit", PIDS_LIMIT,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--network", network,
            *extra_env,
            "-v", f"{win_to_wsl(workdir_host)}:/work", "-w", "/work"]
    if source_host is not None:
        argv += ["-v", f"{win_to_wsl(source_host)}:/src:ro"]
    argv.append(image)
    argv += list(cmd)
    return argv


def sandbox_run(cmd, *, ecosystem, phase="execute", workdir_host, timeout,
                network_allow=None, source_host=None, runner=subprocess.run,
                clock=time.monotonic) -> SandboxResult:
    try:
        image = image_for(ecosystem)
    except UnknownEcosystem as e:
        raise SandboxError(str(e)) from e

    if phase == "install":
        network = "bridge"
        extra_env = safe_install_env(ecosystem)
        hosts = network_allow if network_allow is not None else [registry_for(ecosystem)]
        for host in hosts:
            # Gate declared install egress; ScopeViolation propagates uncaught (audit side-effect).
            check_http(f"https://{host}", bootstrap_hosts=REGISTRY_HOSTS)
    else:
        network = "none"
        extra_env = []

    argv = _build_argv(image, cmd, network=network, workdir_host=workdir_host,
                       source_host=source_host, extra_env=extra_env)

    start = clock()
    timed_out = False
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc = None
    except (FileNotFoundError, OSError) as e:
        raise SandboxError(f"docker invocation failed (is docker reachable in WSL2?): {e}") from e
    duration = clock() - start

    if timed_out:
        result = SandboxResult(exit_code=124, stdout="", stderr="timeout",
                               stdout_sha256=hashlib.sha256(b"").hexdigest(),
                               duration_s=duration, timed_out=True, image=image)
    else:
        stdout = getattr(proc, "stdout", "") or ""
        result = SandboxResult(
            exit_code=getattr(proc, "returncode", 1),
            stdout=stdout, stderr=getattr(proc, "stderr", "") or "",
            stdout_sha256=hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            duration_s=duration, timed_out=False, image=image)

    _append_ledger({"event": "sandbox-exec", "image": image, "phase": phase,
                    "cmd": " ".join(map(str, cmd))[:200], "exit": result.exit_code,
                    "timed_out": result.timed_out, "duration_s": round(duration, 3)})
    return result
```

> Note: `check_http` is imported at module scope so tests can `monkeypatch.setattr(runner_module, "check_http", ...)`. The bare `124` exit code is the conventional timeout code; verify_finding compares against the finding's `expected_exit_code`, so a timeout reads as failure unless a finding genuinely expects 124 (it won't).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_sandbox_runner.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 116 baseline + new sandbox tests, all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/sandbox/runner.py tests/scripts/test_sandbox_runner.py
git commit -m "feat(sandbox): gated hardened sandbox_run chokepoint + ledger audit"
```

---

## Task 3: Readiness check — `doctor.py`

**Files:**
- Create: `scripts/sandbox/doctor.py`
- Create: `tests/scripts/test_sandbox_doctor.py`

**Interfaces:**
- Produces: `sandbox_doctor(*, runner=subprocess.run) -> tuple[bool, list[str]]` (ok, messages). `main(argv=None) -> int`.
- Consumes: `sandbox._images.ECOSYSTEMS`.

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_sandbox_doctor.py`:

```python
import subprocess
import types


def _runner(script):
    """script: callable(argv) -> SimpleNamespace(returncode, stdout, stderr)."""
    def runner(argv, **kw):
        return script(argv)
    return runner


def test_doctor_ok_when_docker_and_images_present():
    from sandbox.doctor import sandbox_doctor
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=0, stdout="Server Version: 27", stderr="")
        if "inspect" in argv:
            return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is True


def test_doctor_fails_when_docker_unreachable():
    from sandbox.doctor import sandbox_doctor
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="Cannot connect")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is False and any("docker" in m.lower() for m in msgs)


def test_doctor_pulls_missing_image():
    from sandbox.doctor import sandbox_doctor
    pulled = []
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        if "inspect" in argv:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="No such image")
        if "pull" in argv:
            pulled.append(argv[-1])
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is True and "node:22-slim" in pulled


def test_doctor_main_returns_one_when_unreachable(monkeypatch):
    import sandbox.doctor as d
    monkeypatch.setattr(d, "sandbox_doctor", lambda **kw: (False, ["docker unreachable"]))
    assert d.main([]) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_sandbox_doctor.py -v`
Expected: FAIL (`No module named 'sandbox.doctor'`).

- [ ] **Step 3: Implement `doctor.py`**

```python
"""sandbox_doctor — verify docker engine is reachable in WSL2 and base images are present.

Fail-closed: if `wsl -e docker info` fails, returns ok=False (callers must not run
sandboxed work). Missing images are pulled (Docker Hub — setup-time infrastructure)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
for _p in (str(SCRIPTS_DIR), str(SCRIPTS_DIR.parent / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sandbox._images import ECOSYSTEMS  # noqa: E402


def _run(runner, argv):
    return runner(["wsl", "-e", "docker", *argv], capture_output=True, text=True)


def sandbox_doctor(*, runner=subprocess.run) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    try:
        info = _run(runner, ["info"])
    except (FileNotFoundError, OSError) as e:
        return False, [f"docker not invokable via WSL2: {e}"]
    if getattr(info, "returncode", 1) != 0:
        return False, [f"docker daemon unreachable in WSL2: {getattr(info, 'stderr', '')[:200]}"]
    msgs.append("docker reachable in WSL2")

    for eco, meta in ECOSYSTEMS.items():
        image = meta["image"]
        inspect = _run(runner, ["image", "inspect", image])
        if getattr(inspect, "returncode", 1) != 0:
            pull = _run(runner, ["pull", image])
            if getattr(pull, "returncode", 1) != 0:
                return False, msgs + [f"failed to pull {image}: {getattr(pull, 'stderr', '')[:200]}"]
            msgs.append(f"pulled {image}")
        else:
            msgs.append(f"{image} present")
    return True, msgs


def main(argv=None) -> int:
    ok, msgs = sandbox_doctor()
    for m in msgs:
        print(("OK: " if ok else "") + m)
    if not ok:
        print("SANDBOX NOT READY — install docker engine in WSL2 (see "
              "docs/superpowers/specs/2026-06-22-stage4a-sandbox-design.md §8).", file=sys.stderr)
        return 1
    print("Sandbox ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scripts/test_sandbox_doctor.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/sandbox/doctor.py tests/scripts/test_sandbox_doctor.py
git commit -m "feat(sandbox): sandbox_doctor fail-closed docker/image readiness check"
```

---

## Task 4: Rewire `verify_finding.py` + `init_workspace` hook + integration smoke

**Files:**
- Modify: `scripts/verify_finding.py` (the `subprocess.run(reproduce.sh)` block, ≈line 76)
- Modify: `scripts/init_workspace.py` (`--verify` path)
- Create: `tests/scripts/test_verify_finding_sandbox.py`

**Interfaces:**
- Consumes: `sandbox.runner.{sandbox_run, SandboxResult, SandboxError}`.

- [ ] **Step 1: Read the current PoC-run block and write the failing tests**

First read `scripts/verify_finding.py` around the `subprocess.run` call (≈line 68-96) and its imports + how it derives the finding's ecosystem (from the finding frontmatter `target.ecosystem`). Match its existing function/return shape.

`tests/scripts/test_verify_finding_sandbox.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/scripts/test_verify_finding_sandbox.py -v`
Expected: FAIL (`run_poc_in_sandbox` not defined / import error).

- [ ] **Step 3: Refactor `verify_finding.py` to a `run_poc_in_sandbox` helper using `sandbox_run`**

Add imports near the top: `from sandbox.runner import sandbox_run, SandboxError`.

Replace the existing direct-`subprocess.run` PoC block with a focused helper (keep the existing determinism logic, now reading from `SandboxResult`):

```python
def run_poc_in_sandbox(*, poc_dir, ecosystem, expected_exit_code, deterministic,
                       expected_hash, timeout):
    """Run poc/reproduce.sh inside the Docker sandbox. Returns (ok, message).

    v1: one-pass with network (install+trigger together) — the immutable finding
    contract. phase='install' so the registry is reachable; host-isolation provides
    containment. Fails closed on SandboxError (no host fallback)."""
    try:
        res = sandbox_run(["bash", "poc/reproduce.sh"], ecosystem=ecosystem,
                          phase="install", workdir_host=poc_dir, timeout=timeout)
    except SandboxError as e:
        return False, f"sandbox unavailable: {e}"

    if res.timed_out:
        return False, f"PoC timed out after {timeout}s"
    if res.exit_code != expected_exit_code:
        return False, f"PoC exit {res.exit_code} != expected {expected_exit_code}"
    if deterministic and res.stdout_sha256 != expected_hash:
        return False, f"PoC stdout hash {res.stdout_sha256} != expected {expected_hash}"
    return True, "PoC reproduced successfully"
```

Then update the caller (the old block around line 68-96) to derive `ecosystem` from the finding frontmatter (`target.ecosystem`; if absent, return `(False, "finding has no target.ecosystem — sandbox needs it")`) and `poc_dir`/`expected_*`/`deterministic` from the loaded finding, and call `run_poc_in_sandbox(...)`. Remove the now-dead `subprocess.run` import if nothing else uses it.

- [ ] **Step 4: Run the verify-finding tests**

Run: `python -m pytest tests/scripts/test_verify_finding_sandbox.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Wire `sandbox_doctor` into `init_workspace.py --verify` (warn-only)**

Read `scripts/init_workspace.py`'s `--verify` path. Add a warn-only sandbox check that does NOT hard-fail workspace init (docker may legitimately not be installed yet):

```python
# in the --verify branch, after existing checks:
try:
    from sandbox.doctor import sandbox_doctor
    ok, msgs = sandbox_doctor()
    print("[sandbox] " + ("ready" if ok else "NOT ready (PoC verification will fail closed): "
                          + "; ".join(msgs)))
except Exception as e:  # never let the optional sandbox check break init
    print(f"[sandbox] check skipped: {e}")
```

- [ ] **Step 6: Add the docker-gated integration smoke**

Append to `tests/scripts/test_sandbox_runner.py` a real-docker smoke that auto-skips when docker is absent:

```python
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
```

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: all green (116 baseline + ~22 new); the integration smoke shows as skipped on this machine (docker not installed yet).

- [ ] **Step 8: Commit**

```bash
git add scripts/verify_finding.py scripts/init_workspace.py tests/scripts/test_verify_finding_sandbox.py tests/scripts/test_sandbox_runner.py
git commit -m "feat(sandbox): rewire verify_finding to sandbox_run + doctor init hook + integration smoke"
```

---

## Verification

**1. Full offline suite:**
```bash
cd sec-research
python -m pytest -q
```
Expected: all green (116 baseline + new). The docker-gated integration smoke is SKIPPED (docker not yet installed) — that is expected and correct.

**2. Fail-closed proof (no uncontained path):** confirm `verify_finding` cannot run a PoC on the host when docker is absent — covered by `test_verify_sandbox_error_fails_closed`. Spot-check that `verify_finding.py` no longer calls `subprocess.run` on `reproduce.sh` directly (`grep -n "subprocess.run" scripts/verify_finding.py` should not show the PoC line).

**3. Doctor:** `python scripts/sandbox/doctor.py` → prints "SANDBOX NOT READY" + exit 1 on this machine (docker absent). After installing docker engine in WSL2 (§8 of the spec), re-run → "Sandbox ready." and the integration smoke un-skips.

**4. Argv hardening:** `test_execute_phase_builds_hardened_no_network_argv` pins `--network none`, `--cap-drop ALL`, `no-new-privileges`, memory/cpu/pids limits, correct image, and the path-translated mount — the containment contract is asserted from the constructed argv.

---

## Retrospective

**Issue state:** Closes hb-wy4 (Stage 4a guarded sandboxed subprocess layer). Follows up hb-ahp. Follow-ups discovered during implementation should be filed as new beads (`Follows up hb-wy4`) — likely: install docker engine in WSL2 + real-container validation; phased `--network none` execution via `poc.preconditions` install/trigger split (4c); malicious-pkg install hardening via egress-allowlist proxy; pip/cargo/gem install-script neutralization (only npm gets env-based neutralization in v1).

- **What worked:**
- **Friction / surprises:**
- **WSL2-docker reality** (did `wsl -e docker` argv + `/mnt/c` mounts behave as assumed once docker was installed? what changed?):
- **Follow-ups discovered:**
