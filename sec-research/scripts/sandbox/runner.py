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

# Drop root for the execute (trigger) phase: the untrusted PoC runs as an
# unprivileged uid:gid. The install phase stays root so it can write node_modules
# into /work (the install→trigger channel); the trigger only reads /work + runs the
# interpreter, and npm/pip/etc. write world-readable trees, so a non-root reader is
# fine. Numeric uid keeps this image-agnostic. Per-phase --read-only / install-script
# neutralization for pip/cargo/rubygems is deferred to hb-nxz.
EXEC_USER = "1000:1000"


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


def _safe_mount(host_path) -> str:
    """Translate a host path to a WSL path and require it to be a real Windows drive mount."""
    wsl = win_to_wsl(host_path)
    if not wsl.startswith("/mnt/"):
        raise SandboxError(f"refusing to mount non-Windows host path: {host_path!r}")
    return wsl


def _build_argv(image, cmd, *, network, workdir_host, source_host, extra_env, user=None) -> list[str]:
    argv = ["wsl", "-e", "docker", "run", "--rm",
            "--memory", MEM_LIMIT, "--cpus", CPU_LIMIT, "--pids-limit", PIDS_LIMIT,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--network", network]
    if user is not None:
        argv += ["--user", user]
    argv += [*extra_env,
             "-v", f"{_safe_mount(workdir_host)}:/work", "-w", "/work"]
    if source_host is not None:
        argv += ["-v", f"{_safe_mount(source_host)}:/src:ro"]
    argv.append(image)
    argv += list(cmd)
    return argv


def sandbox_run(cmd, *, ecosystem, phase="execute", workdir_host, timeout,
                network_allow=None, source_host=None, runner=subprocess.run,
                clock=time.monotonic) -> SandboxResult:
    """Run cmd inside a hardened docker container via wsl.

    Args:
        cmd: Command + args to run inside the container.
        ecosystem: One of npm/pypi/cargo/rubygems — selects image, registry, env.
        phase: "execute" (--network none) or "install" (--network bridge + egress gate).
        workdir_host: Windows host path mounted at /work inside the container.
        timeout: Wall-clock timeout in seconds. Timeout → timed_out=True result, NOT a raise.
        network_allow: Install-phase hosts to gate via check_http. Defaults to [registry_for(ecosystem)].
        source_host: Optional Windows host path mounted read-only at /src inside the container.
        runner: Injectable subprocess.run replacement for offline tests.
        clock: Injectable time.monotonic replacement for tests.

    Raises:
        SandboxError: Docker/wsl not reachable, or unknown ecosystem.
        ScopeViolation: Install-phase host blocked by policy (propagates uncaught).
    """
    if phase not in ("execute", "install"):
        raise SandboxError(f"invalid phase {phase!r} (expected 'execute' or 'install')")

    try:
        image = image_for(ecosystem)
    except UnknownEcosystem as e:
        raise SandboxError(str(e)) from e

    if phase == "install":
        network = "bridge"
        extra_env = safe_install_env(ecosystem)
        hosts = network_allow if network_allow is not None else [registry_for(ecosystem)]
        if not hosts:
            raise SandboxError("install phase requires at least one host in network_allow")
        for host in hosts:
            h = host.strip()
            if not h or any(c in h for c in "/@: \t"):
                raise SandboxError(f"invalid install host {host!r} (bare hostname required)")
            # Gate declared install egress; ScopeViolation propagates uncaught (audit side-effect).
            check_http(f"https://{h}", bootstrap_hosts=REGISTRY_HOSTS)
    else:
        network = "none"
        extra_env = []

    user = EXEC_USER if phase == "execute" else None
    argv = _build_argv(image, cmd, network=network, workdir_host=workdir_host,
                       source_host=source_host, extra_env=extra_env, user=user)

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
