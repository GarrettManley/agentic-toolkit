# Design: Stage 4a — Guarded Sandboxed Subprocess Layer

**Trace ID**: trace-20260622-001 (Stage 4, sub-project a of 3)
**Status**: APPROVED 2026-06-22
**Charter**: `docs/CHARTER.md` (§Known limitation — the subprocess-scope-gap prerequisite)
**Predecessor**: Stage 3 Recon Module — plan `docs/superpowers/plans/2026-06-21-stage3-recon.md` (shipped; tracker hb-ahp)
**Tracker**: hb-wy4 (Follows up hb-ahp)

---

## 1. Introduction

### 1.1 Why Stage 4 is decomposed

Stage 4 ("Hypothesis & Test Harness") spans three distinct subsystems: a **subprocess
scope-check wrapper**, **LLM hypothesis generation**, and a **sandboxed verification harness**.
Each is its own spec → plan → build cycle:

- **4a (this spec)** — the guarded sandboxed subprocess layer. The CHARTER-mandated security
  prerequisite; foundational and independently shippable.
- **4b** — hypothesis generation (LLM reads the recon item + playbooks → candidate hypotheses).
- **4c** — verification harness (orchestrates hypotheses → guarded PoC runs → evidence →
  verified/refuted).

4a must land first: it is the only thing that makes live PoC execution safe, and 4c depends on it.

### 1.2 Purpose

Today PoC execution is **uncontained**: `scripts/verify_finding.py` runs `poc/reproduce.sh`
directly via `subprocess.run` (its own comment: "Stage 4 will switch to sandbox_server.py"),
and `sandbox_server.py` does not exist. PT-5's "must run in sandbox" check is currently a string
test (`docker`/`sandbox_server` substring) with **nothing behind it**. 4a builds the real thing:
a single audited chokepoint that executes risky subprocesses (registry installs, PoC scripts)
inside a Docker container, host-isolated, with declared-egress gating and ledger audit, and
rewires `verify_finding.py` to use it.

### 1.3 Scope

In scope: a `scripts/sandbox/` package exposing `sandbox_run` (the chokepoint), `sandbox_doctor`
(fail-closed readiness check), ecosystem→image mapping, and Windows→WSL2 path translation; and
the `verify_finding.py` rewire. Out of scope (§9): hypothesis generation (4b), the verification
harness/pipeline wiring (4c), phased `--network none` execution for findings, malicious-pkg
install hardening via an egress-allowlist proxy.

### 1.4 The containment constraint (immutable finding contract)

`schema/finding.schema.json` is Stage-1 immutable. Its `poc.reproduce_script` is a single
`poc/reproduce.sh` that performs **both install and trigger**. There is no field separating
setup from trigger. Therefore v1 runs `reproduce.sh` **one-pass with network enabled** (install
needs the registry), relying on host-isolation for containment. The `sandbox_run` primitive is
nonetheless built **phase-capable** (`execute` → `--network none`; `install` → gated bridge) so
4c can later adopt phased no-network execution by moving install commands into the optional
`poc.preconditions` field — a finding-authoring convention change, **no schema change**.

---

## 2. Background

| Asset | Path | Relevance |
|-------|------|-----------|
| Uncontained PoC runner | `scripts/verify_finding.py` (≈line 76, `subprocess.run`) | the call site 4a rewires |
| PT-5 sandbox gate | `hooks/pretooluse.py::check_pt5_sandbox` (≈line 262) | blocks installs/PoC unless cmd contains `docker`/`sandbox_server`; 4a makes the bypass real |
| Scope gate | `hooks/lib/policy.py::check_http(url, *, bootstrap_hosts=...)`, `ScopeViolation` | declared-host gating for the install phase; ledger side-effect |
| Ledger | `submissions/ledger.jsonl` | append `sandbox-exec` audit events |
| Finding/PoC schema | `schema/finding.schema.json` (`poc.reproduce_script`, `expected_exit_code`, `deterministic`, `expected_output_hash`, `preconditions`) | the determinism contract `sandbox_run` feeds |
| Stage 2/3 package + injected-runner test pattern | `scripts/fetchers/`, `scripts/recon/clone.py` | the conventions 4a mirrors |
| Environment | WSL2 v2.3.26 present; **no Docker installed anywhere** (no Desktop, none in WSL2) | 4a includes installing docker engine in WSL2 |

**Decisions locked during brainstorming:** Stage 4 decomposed (4a first); containment via
Docker; Docker runtime = **docker engine inside WSL2** (no Docker Desktop), invoked
`wsl -e docker …` with `/mnt/c` path translation; module lives in `scripts/sandbox/`; v1 wiring
is one-pass-with-network + host-isolation (phased no-network deferred to 4c); installing docker
in WSL2 is a 4a prerequisite that `sandbox_doctor` verifies fail-closed.

---

## 3. Requirements

### 3.1 Functional

- **R1** — `sandbox_run(cmd, *, ecosystem, phase="execute", workdir_host, timeout, network_allow=None, runner=subprocess.run) -> SandboxResult` executes `cmd` inside a Docker container via `wsl -e docker run`, returning `SandboxResult(exit_code, stdout, stderr, stdout_sha256, duration_s, timed_out, image)`.
- **R2** — Container hardening on **every** run: `--rm`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--memory`/`--cpus`/`--pids-limit`, the host workdir mounted, the cloned source mounted **read-only**, and a wall-clock timeout (kills the container).
- **R3** — Phase→network mapping: `phase="execute"` → `--network none`; `phase="install"` → bridge network + ecosystem `--ignore-scripts`-equivalent, AND every host in `network_allow` gated via `policy.check_http(...)` before dispatch.
- **R4** — `ecosystem` selects a pinned base image (node / python / rust / ruby) from `_images.py`. Unknown ecosystem → `SandboxError`.
- **R5** — Windows host paths are translated to `/mnt/c/...` for the `wsl -e docker` mount (`_wslpath.py`).
- **R6** — Every run appends a `sandbox-exec` event to `submissions/ledger.jsonl` (image, phase, cmd-summary, exit, duration) — best-effort, never suppresses the result/raise.
- **R7** — `sandbox_doctor()` (CLI `python scripts/sandbox/doctor.py`, plus an `init_workspace.py --verify` hook) checks `wsl -e docker info` reachable and base images present (pulls if missing); returns non-zero / raises when docker is unreachable.
- **R8** — `verify_finding.py` runs `poc/reproduce.sh` via `sandbox_run` instead of direct `subprocess.run`, feeding the existing exit-code + `stdout_sha256` determinism checks from `SandboxResult`.

### 3.2 Constraints (invariants — hard)

- **C1 — No uncontained path survives.** When docker is unreachable, `sandbox_run` raises
  `SandboxError`; it never silently falls back to direct host execution. `verify_finding.py`
  surfaces the error rather than running the PoC on the host.
- **C2 — Stage 1 is the contract.** No modification to `schema/*.json`, `hooks/policy.py`, or any
  hook. The recon/registry allow-set is passed via `check_http`'s `bootstrap_hosts` parameter.
  The only existing file modified is `scripts/verify_finding.py` (the rewire) and
  `scripts/init_workspace.py` (optional doctor hook).
- **C3 — Declared egress gated.** Install-phase network hosts pass through `policy.check_http`
  before the container starts; `ScopeViolation` propagates uncaught (it carries the ledger
  side-effect) and is handled only at the CLI top level.
- **C4 — Host isolation.** The container cannot write the host filesystem outside the mounted
  workdir; cloned source is read-only; no `--privileged`; capabilities dropped.
- **C5 — Offline-testable.** `sandbox_run` accepts an injected `runner` so the unit suite
  constructs/asserts the docker command with zero docker/wsl invocation; the one real-docker
  test is gated and auto-skips when docker is absent.

---

## 4. Architecture

```
scripts/sandbox/
  __init__.py
  runner.py     # sandbox_run(...) -> SandboxResult ; SandboxResult, SandboxError ; the chokepoint
  doctor.py     # sandbox_doctor(): wsl -e docker reachability + image presence; CLI main()
  _images.py    # ECOSYSTEM_IMAGES: ecosystem -> pinned base image tag
  _wslpath.py   # win_to_wsl(path) -> "/mnt/c/..." for docker -v mounts
```

`runner.py` is the only component that shells out to `wsl -e docker`. `verify_finding.py` (and,
later, 4c) import `from sandbox.runner import sandbox_run, SandboxResult, SandboxError`. The
package lives under `scripts/` (on `sys.path` via conftest) — deliberately **not** `hooks/lib/`,
to keep docker-shelling code out of the PreToolUse hot path.

### Data flow (v1, via verify_finding.py)

`verify_finding(<trace>)` → locate `findings/<trace>/poc/reproduce.sh` → `sandbox_run(["bash","poc/reproduce.sh"], ecosystem=<from finding target>, phase="execute"|"install", workdir_host=<finding poc dir>, timeout=…)` → container runs hardened, `--network none` if execute / gated-bridge if install → `SandboxResult` → verify_finding compares `exit_code`==`expected_exit_code` and (if `deterministic`) `stdout_sha256`==`expected_output_hash` → ledger `sandbox-exec` event written.

> v1 calls `reproduce.sh` in a single pass with network (install+trigger together — the immutable
> finding contract), so v1 effectively uses the `install`-phase network policy for the whole
> script. The `execute`/`--network none` path is exercised by tests and reserved for 4c once
> findings split setup (→ `poc.preconditions`) from trigger.

---

## 5. Detailed design

### 5.1 `sandbox_run` (runner.py)

Builds and runs:
```
wsl -e docker run --rm
  --memory <M> --cpus <C> --pids-limit <P>
  --cap-drop ALL --security-opt no-new-privileges
  --network none|bridge
  -v <wsl-workdir>:/work -w /work
  [-v <wsl-source>:/src:ro]
  <image> <cmd...>
```
- `phase="install"`: `--network bridge`; before building the command, call
  `policy.check_http(f"https://{host}", bootstrap_hosts=…)` for each `network_allow` host (raise
  `ScopeViolation` on block); inject the ecosystem `--ignore-scripts`-equivalent into known
  package-manager commands.
- `phase="execute"`: `--network none`.
- Capture stdout/stderr; compute `stdout_sha256`; enforce `timeout` (on `subprocess.TimeoutExpired`
  → `timed_out=True`, kill container); map runtime/docker failures (non-zero `wsl -e docker`
  invocation, image missing) to `SandboxError`.
- Append the `sandbox-exec` ledger event (best-effort).

### 5.2 `_images.py`
`ECOSYSTEM_IMAGES = {"npm": "node:<lts>-slim", "pypi": "python:<ver>-slim", "cargo": "rust:<ver>-slim", "rubygems": "ruby:<ver>-slim"}` — pinned tags. Unknown ecosystem → `SandboxError`.

### 5.3 `_wslpath.py`
`win_to_wsl(p: Path) -> str`: `C:\Users\…` → `/mnt/c/Users/…` (drive-letter lowercase, backslashes → forward slashes). Pure function, trivially unit-tested.

### 5.4 `doctor.py`
`sandbox_doctor() -> tuple[bool, list[str]]`: runs `wsl -e docker info` (via injected runner in
tests); checks each `ECOSYSTEM_IMAGES` tag present (`docker image inspect`), pulling if absent
(`docker pull`, an infra action). CLI `main()` prints status, exits non-zero if docker
unreachable. Wired as an optional check in `init_workspace.py --verify`.

### 5.5 `verify_finding.py` rewire
Replace the direct `subprocess.run(reproduce.sh, …)` block with `sandbox_run(...)`; derive
`ecosystem` from the finding's `target.ecosystem`; keep the existing exit-code + hash
determinism assertions, now reading from `SandboxResult`. On `SandboxError` (docker unreachable),
verify fails with a clear message — no host fallback (C1).

---

## 6. Error handling

- **Docker unreachable** → `SandboxError`; verify_finding fails closed (C1). `sandbox_doctor`
  surfaces it ahead of time.
- **Timeout** → container killed, `timed_out=True`, non-zero result (verify treats as failure).
- **Image missing at run time** → `SandboxError` directing the user to run `sandbox_doctor`.
- **`ScopeViolation`** (install-phase host out of scope) → propagates uncaught → CLI exit 1.
- **Non-zero PoC exit** → returned in `SandboxResult` (verify compares to `expected_exit_code`).

---

## 7. Testing strategy

Offline, TDD, mirroring Stage 2/3:

- **Unit (default, no docker):** injected `runner` asserts the exact `wsl -e docker run`
  argv — image per ecosystem, `--network none` for execute vs `bridge` for install, `--cap-drop
  ALL`/`no-new-privileges`/memory/cpus/pids, read-only source mount, `/mnt/c` path translation,
  `--ignore-scripts` injection on install; phase→network mapping; `check_http` called for each
  install host **before** the run; `ScopeViolation` and `SandboxError` propagation; `stdout_sha256`
  computation; timeout → `timed_out`; ledger `sandbox-exec` append. `_wslpath` and `_images`
  pure-function tests.
- **Integration smoke (gated):** one real `wsl -e docker run hello-world`-class test, auto-skipped
  via a docker-availability check so the suite stays green on this machine until docker is
  installed.
- **verify_finding rewire:** test that it calls `sandbox_run` (injected) and maps
  `SandboxResult` → determinism verdict; that `SandboxError` fails verification (no host run).

---

## 8. Prerequisite: Docker engine in WSL2

4a includes standing up docker engine **inside the existing WSL2 distro** (not Docker Desktop):
documented setup steps + `sandbox_doctor` verification. Until docker is reachable, the integration
smoke skips and `verify_finding` fails closed — no uncontained execution path exists at any point.

**Image-pull egress:** pulling the pinned base images hits Docker Hub
(`registry-1.docker.io` / `auth.docker.io`) — treated as build/setup **infrastructure**
(analogous to Stage 3's `RECON_INFRA_HOSTS`), performed by `sandbox_doctor` at setup time, not
inside any per-program scoped run. This egress is the `docker pull` mechanism itself, not a
`check_http`-gated call; document it as a known, setup-time infrastructure dependency.

---

## 9. Out of scope (this sub-project)

- LLM hypothesis generation (Stage 4b) and the verification harness + pipeline `stage_verify`
  wiring (Stage 4c).
- Phased `--network none` execution for real findings (needs install/trigger split via
  `poc.preconditions` — a 4c finding-authoring follow-up; the primitive already supports it).
- Malicious-pkg install hardening via an egress-allowlist HTTP proxy (v1 uses `--ignore-scripts`
  + gated bridge; the supply-chain-malicious-pkg class needs the proxy before its installs are
  fully safe).
- Non-{npm,pypi,cargo,rubygems} ecosystems.

---

## 10. References

- `docs/CHARTER.md` §Known limitation (the subprocess-scope-gap this sub-project closes).
- `docs/HOOK_CONTRACTS.md` — PT-5 (sandbox), PoT-3 (timeline).
- `docs/EVIDENCE_DISCIPLINE.md` — PoC + evidence requirements `verify_finding` enforces.
- `schema/finding.schema.json` — the immutable `poc.*` determinism contract.
- `hooks/lib/policy.py` — `check_http` / `ScopeViolation` (install-phase gating).

---

## 11. History

| Date | Change |
|------|--------|
| 2026-06-22 | Initial design. Decisions locked in brainstorm: Stage 4 decomposed (4a wrapper first → 4b hypothesis → 4c harness); Docker containment via **docker engine in WSL2** (`wsl -e docker`, `/mnt/c` mounts); `scripts/sandbox/` package; phase-capable primitive but v1 wires one-pass-with-network + host-isolation (phased no-network deferred to 4c, no schema change); docker-in-WSL2 install is a 4a prerequisite verified fail-closed by `sandbox_doctor`. Confirmed: Docker absent on this machine (no Desktop, none in WSL2). |
