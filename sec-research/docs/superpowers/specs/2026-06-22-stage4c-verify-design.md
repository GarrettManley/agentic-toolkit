# Design: Stage 4c — Sandboxed Verification Harness

**Trace ID**: trace-20260622-003 (Stage 4, sub-project c of 3)
**Status**: Draft
**Charter**: `docs/CHARTER.md` (§Stages — 4c closes the hypothesis→evidence gap)
**Predecessor**: Stage 4a (sandbox) — plan `docs/superpowers/plans/2026-06-22-stage4a-sandbox.md` (shipped; tracker hb-wy4); Stage 4b (hypotheses) — tracker hb-oec (shipped)
**Tracker**: hb-s2c (Follows up hb-oec)

---

## 1. Introduction

### 1.1 Why Stage 4 is decomposed

Stage 4 ("Hypothesis & Test Harness") spans three distinct subsystems, each its own
spec → plan → build cycle:

- **4a** — the guarded sandboxed subprocess layer (shipped, hb-wy4). The CHARTER-mandated
  security prerequisite; provides `sandbox_run`, `SandboxResult`, `SandboxError`, and
  `sandbox_doctor`.
- **4b** — hypothesis generation (shipped, hb-oec). LLM reads recon item + playbooks → emits
  scope-bounded, schema-validated hypotheses to `runtime/hypotheses/<slug>/hypotheses.json`.
- **4c (this spec)** — the verification harness. Turns each hypothesis into a per-hypothesis
  PoC, runs it through the Stage-4a sandbox with a phased install→trigger split, and emits
  `verified / refuted / skipped / error` verdicts backed by deterministic evidence.

4c depends on both 4a (the sandbox primitive) and 4b (the hypothesis feed). It is the gate
that stops un-reproduced hypotheses from ever reaching finding-drafting (Stage 6).

### 1.2 Purpose

Stage 4b leaves `nightly.stage_verify` as a stub that rubber-stamps every hypothesis as
unverified. 4c replaces that stub with a real harness: a `PocStrategy` Protocol that builds a
two-phase `PocPlan` (install → trigger), drives it through `sandbox_run` (Stage 4a, reused
as-is), and derives a typed `Verdict` from the trigger's `exit_code` + `stdout_sha256`. Every
verdict is persisted to `runtime/verdicts/<slug>/verdicts.json` and appended to the ledger.

The key-contract: **`verified` means the PoC actually triggered observable vulnerable behavior
in the sandbox, captured deterministically via `exit_code` + `stdout_sha256`** — not mere
version-in-range confirmation. This distinction is load-bearing: Stage 6 (finding-drafting) is
only reached for `verified` hypotheses.

### 1.3 Scope

**In scope:** `PocStrategy` Protocol + templated strategy + one real exploit template; phased
install→trigger harness; verdict/evidence model; `runtime/verdicts/` persistence;
`nightly.stage_verify` wiring; offline unit tests + one docker-gated live test; this spec +
plan docs.

**Out of scope (§10):** finding markdown / `findings/<trace>/` drafting (stays Stage 6
`stage_draft_findings`, untouched); LLM-backed PoC authoring (seam defined, not wired); any
`schema/*.json` change (finding and hypothesis contracts are Stage-1 locked);
non-deterministic-output exploit classes; ecosystems beyond the vertical slice's npm.

### 1.4 The reconciliation boundary (the one hard constraint)

Two user-locked design decisions govern 4c:

1. **PoC authoring = Hybrid.** A `PocStrategy` Protocol; a deterministic **templated** strategy
   ships in v1; an **LLM-backed** strategy is defined-but-not-wired behind the same Protocol.
2. **Verification depth = Full exploit reproduction.** `verified` requires the PoC to *actually
   trigger* observable vulnerable behavior captured via `exit_code` + `stdout_sha256`.

These are jointly satisfiable only for exploits whose success collapses to a **constant sentinel
string + exit code** (variable output — timings, leaked secrets, addresses — kept out of stdout,
used only to *select* the sentinel). v1's templated strategy is restricted to that subset;
everything else is explicitly the LLM seam's future territory. This keeps v1 small, fully
deterministic, and reproducible.

---

## 2. Background

| Asset | Path | Relevance |
|-------|------|-----------|
| Sandbox chokepoint | `scripts/sandbox/runner.py:77` `sandbox_run(cmd, *, ecosystem, phase, workdir_host, timeout, network_allow=None, runner=subprocess.run, …) -> SandboxResult` | the reused execution primitive; 4c calls it directly for the two-phase split |
| Phase→network | `scripts/sandbox/runner.py:105-119` | `phase="install"` → bridge + `check_http` per host; `phase="execute"` → `--network none` |
| LLM generate patterns | `scripts/llm/generate.py:48-103` | per-item isolation, ledger-event, and `_persist`-grouped-by-slug patterns to mirror in shape |
| Protocol + dispatch shape | `scripts/llm/client.py:31-48` | `@runtime_checkable Protocol` + `select_*()` dispatch — template for `PocStrategy` / `select_strategy` |
| Scope gate | `hooks/lib/policy.py` | `check_http`, `ScopeViolation`, `is_in_scope`; `ScopeViolation` propagates uncaught from any install-phase run |
| Ledger writer | `hooks/lib/ledger.py:46` `append_event(...)` | audited JSON-line writer 4b already uses; reuse for 4c events |
| evidence_seed delegation | `schema/hypothesis.schema.json:40-43` | schema delegates required-field completeness enforcement to 4c's strategy |
| Hypothesis feed | `runtime/hypotheses/<slug>/hypotheses.json` | 4c's input; written by 4b |
| Verdict output | `runtime/verdicts/<slug>/verdicts.json` | 4c's primary output; raw evidence gitignored at `runtime/verdicts/<slug>/evidence/` |
| Uncontained PoC runner (NOT reused) | `scripts/verify_finding.py:66` `run_poc_in_sandbox` | single-pass `phase="install"` for the immutable *finding* contract; 4c does NOT reuse this — it calls `sandbox_run` directly for the two-phase split |
| npm install env hardening | `scripts/sandbox/_images.py:16` `npm_config_ignore_scripts=true` | the fetched vulnerable package's lifecycle scripts don't run; only `trigger.js` executes |
| Stage 1 hypothesis schema | `schema/hypothesis.schema.json` | Stage-1 immutable; no changes in 4c |

**Decisions locked during brainstorming:** PoC authoring is Hybrid (templated v1 + LLM seam);
verification depth is full exploit reproduction; constant-sentinel constraint defines v1's
template scope; `scripts/verify/` is a new package sibling to `scripts/sandbox/` and
`scripts/llm/`; `stage_verify` in `nightly.py` is the only existing file modified (plus the
report `task-0-report.md`); `runtime/verdicts/` layout mirrors `runtime/hypotheses/`;
`ScopeViolation` propagates uncaught from install-phase runs.

---

## 3. Requirements

### 3.1 Functional

- **R1 — Phased install→trigger execution.** For each hypothesis, materialize the PoC plan's
  files into a per-hypothesis host workdir `runtime/verdicts/<slug>/work/<hypothesis_id>/`,
  then drive two `sandbox_run` calls: install (`phase="install"`, `--network bridge`,
  `check_http`-gated per declared host) followed by trigger (`phase="execute"`,
  `--network none`). Both phases share the same host workdir as the handoff channel
  (`node_modules/` written by install, read by trigger). Install failure (non-zero exit or
  timeout) short-circuits: trigger is never attempted, verdict is `error`.

- **R2 — Verdict derived from trigger only.** `verdict = "verified"` iff
  `trigger.exit_code == plan.expected_trigger_exit AND trigger.stdout_sha256 == plan.expected_trigger_sha256`.
  Ran-but-mismatch → `"refuted"` (records actual-vs-expected in `reason`). `timed_out` →
  `"error"`. Install evidence is retained as supporting evidence, not part of the verdict
  decision.

- **R3 — evidence_seed completeness validation.** Before calling `strategy.build_plan()`,
  validate that all required fields are present and non-blank in the hypothesis's
  `evidence_seed`. Templated dependency-cve requires: `package_ecosystem`, `package_name`,
  `affected_versions_range`, `candidate_cve_id`. Missing or blank → verdict `"skipped"` +
  `verify-seed-incomplete` ledger event + `continue` (exact analogue of 4b's
  `hypothesis-invalid` skip). `"skipped"` ≠ `"refuted"`: `"refuted"` means "PoC ran and
  didn't reproduce."

- **R4 — `PocStrategy` Protocol with templated v1 + LLM seam.** Define
  `PocStrategy(@runtime_checkable Protocol)` with `supports(hypothesis: dict) -> bool` and
  `build_plan(hypothesis: dict) -> PocPlan`. `TemplatedPocStrategy` implements the Protocol
  via `TEMPLATE_REGISTRY` keyed `(ecosystem, package, cve)`. `LLMPocStrategy` is
  defined-behind-Protocol: `supports() → False`, `build_plan() → NotImplementedError` (seam
  only, not wired). `select_strategy(name=None)` reads env `SECRESEARCH_POC_STRATEGY`,
  default `"templated"`.

- **R5 — Persist verdicts to `runtime/verdicts/`.** After each batch, persist verdicts
  grouped by program slug to `runtime/verdicts/<slug>/verdicts.json`; persist raw per-phase
  stdout to gitignored `runtime/verdicts/<slug>/evidence/<hypothesis_id>/{install,trigger}.stdout.txt`.
  Verdicts only — no finding markdown, no Trace-ID minted.

- **R6 — Wire `nightly.stage_verify`.** Replace the stub in `nightly.py` with a call to
  `verify.harness.verify_hypotheses(...)`. `stage_verify` returns `list[dict]`, each being
  `asdict(Verdict)` plus a derived `"verified": bool` key so `stage_briefing`'s counter at
  `nightly.py:102` needs no change. This is the only modification to `nightly.py`.

### 3.2 Constraints (invariants — hard)

- **C1 — `ScopeViolation` propagates uncaught.** Never wrap the install `sandbox_run` call in
  a handler that catches `ScopeViolation` (it is `Exception`, not `SandboxError`; it carries a
  `policy-blocked` ledger side-effect). Catch only `SandboxError` and `SeedIncomplete` per item.

- **C2 — Trigger is `--network none`.** The trigger phase must always run airgapped. Asserted
  in unit tests against the constructed argv.

- **C3 — Fail-closed when sandbox unavailable.** Docker unreachable → all verdicts in the
  batch are `"error"`; never `"verified"`; never a direct-host fallback. `SandboxError` per
  item → `error` verdict + `verify-sandbox-error` ledger event + continue.

- **C4 — No schema changes.** `schema/*.json` is Stage-1 immutable. The hypothesis and
  finding schemas are not modified. The verdict model lives in `scripts/verify/model.py`,
  not in the schema dir.

- **C5 — No finding markdown / verdicts only.** 4c emits `runtime/verdicts/` only. No
  `findings/<trace>/` directory, no Trace-ID, no finding.md, no evidence/ under findings/.
  Stage 6 owns finding creation.

- **C6 — Per-item isolation.** One docker hiccup or seed-incomplete hypothesis must never
  kill the rest of the batch. `except SandboxError → verdict=error + ledger + continue`
  mirrors 4b's `except LLMUnavailable` pattern.

---

## 4. Architecture

New package `scripts/verify/`, sibling to `scripts/sandbox/` and `scripts/llm/`. `scripts/`
is on `sys.path` via `tests/conftest.py:18-20`, so `from verify.harness import …` and
`from sandbox.runner import …` resolve without path surgery.

```
hypotheses(list[dict]) ─► stage_verify ─► verify.harness.verify_hypotheses
                                              │  per hypothesis (isolated):
   select_strategy() ──► PocStrategy ◄────────┤  1. strategy.supports? else skip
     ├─ TemplatedPocStrategy (v1)             │  2. validate evidence_seed completeness
     └─ LLMPocStrategy (stub, not wired)      │  3. strategy.build_plan() -> PocPlan
                                              │  4. _drive_phased:
   sandbox.runner.sandbox_run ◄───────────────┤       install (phase=install, --network bridge,
     (Stage 4a, reused as-is)                 │               check_http-gated per host)
                                              │       trigger (phase=execute, --network none)
                                              │  5. verdict = f(trigger.exit_code,
                                              │                  trigger.stdout_sha256)
                                              ▼
                              runtime/verdicts/<slug>/verdicts.json
                              runtime/verdicts/<slug>/evidence/<id>/{install,trigger}.stdout.txt
                              (evidence/ gitignored; work/ gitignored)
```

### File decomposition

| File | Responsibility |
|------|----------------|
| `scripts/verify/__init__.py` | package marker (empty) |
| `scripts/verify/model.py` | `EvidenceCapture`, `Verdict` frozen dataclasses; `VERDICT_VERIFIED` / `VERDICT_REFUTED` / `VERDICT_SKIPPED` / `VERDICT_ERROR` constants; pure `derive_verdict(trigger, plan) -> str` helper |
| `scripts/verify/strategy.py` | `PocPlan` dataclass; `PocStrategy` `@runtime_checkable Protocol`; `SeedIncomplete(ValueError)`; `select_strategy(name=None) -> PocStrategy` (env `SECRESEARCH_POC_STRATEGY`, default `"templated"`) |
| `scripts/verify/templated.py` | `TemplatedPocStrategy` + `TEMPLATE_REGISTRY` keyed `(ecosystem, package, cve)` |
| `scripts/verify/templates/npm__minimatch__CVE-2022-3517.py` | vertical-slice exploit template; produces a `PocPlan` |
| `scripts/verify/llm_strategy.py` | `LLMPocStrategy` — defined behind Protocol; `supports()→False`, `build_plan()→NotImplementedError` (seam only) |
| `scripts/verify/harness.py` | `verify_hypotheses(hypotheses, slug, *, strategy=None) -> list[dict]` orchestrator; `_drive_phased(plan, hypothesis_id, slug) -> tuple[EvidenceCapture, EvidenceCapture]`; `_persist(verdicts, slug)`; `RUNTIME_VERDICTS_DIR` |

---

## 5. Detailed design

### 5.1 `model.py`

```python
VERDICT_VERIFIED = "verified"
VERDICT_REFUTED  = "refuted"
VERDICT_SKIPPED  = "skipped"
VERDICT_ERROR    = "error"

@dataclass(frozen=True)
class EvidenceCapture:
    phase: str          # "install" | "trigger"
    exit_code: int
    stdout_sha256: str
    timed_out: bool
    duration_s: float

@dataclass(frozen=True)
class Verdict:
    hypothesis_id: str
    program_slug: str
    target_identifier: str
    vuln_class: str
    verdict: str        # one of VERDICT_* constants
    reason: str
    strategy: str       # e.g. "templated"
    template_id: str | None
    evidence: list[EvidenceCapture]
    verified_at: str    # ISO-8601 UTC
```

`derive_verdict(trigger: EvidenceCapture, plan: PocPlan) -> str` is a pure function (no
sandbox calls): if `trigger.timed_out` → `VERDICT_ERROR`; elif `trigger.exit_code ==
plan.expected_trigger_exit and trigger.stdout_sha256 == plan.expected_trigger_sha256` →
`VERDICT_VERIFIED`; else → `VERDICT_REFUTED`.

### 5.2 `strategy.py`

`PocPlan` carries:
- `files: dict[str, str]` — filename → content, materialized into the workdir before install.
- `install_cmd: list[str]` — e.g. `["npm", "install", "minimatch@3.0.4"]`.
- `install_hosts: list[str]` — passed as `network_allow` to the install `sandbox_run`.
- `trigger_cmd: list[str]` — e.g. `["node", "trigger.js"]`.
- `expected_trigger_exit: int` — 0 for ReDoS sentinel success.
- `expected_trigger_sha256: str` — sha256 of the expected constant sentinel output.
- `ecosystem: str` — e.g. `"npm"`.

`PocStrategy` Protocol:
```python
@runtime_checkable
class PocStrategy(Protocol):
    def supports(self, hypothesis: dict) -> bool: ...
    def build_plan(self, hypothesis: dict) -> PocPlan: ...
```

`SeedIncomplete(ValueError)` — raised by `build_plan` when required `evidence_seed` fields
are missing; caught in `verify_hypotheses` and converted to a `skipped` verdict.

`select_strategy(name=None) -> PocStrategy`: reads `os.environ.get("SECRESEARCH_POC_STRATEGY",
"templated")`; maps `"templated"` → `TemplatedPocStrategy()`, `"llm"` → `LLMPocStrategy()`;
unknown name → `ValueError`.

### 5.3 `templated.py`

`TEMPLATE_REGISTRY: dict[tuple[str, str, str], Callable[[dict], PocPlan]]` — keyed
`(ecosystem, package_name, candidate_cve_id)`. `TemplatedPocStrategy.supports(hypothesis)`:
extracts the triple from `hypothesis["evidence_seed"]` and returns
`triple in TEMPLATE_REGISTRY`. `TemplatedPocStrategy.build_plan(hypothesis)`: looks up and
calls the registered callable; raises `SeedIncomplete` if any required field is missing.

Required seed fields for dependency-cve: `package_ecosystem`, `package_name`,
`affected_versions_range`, `candidate_cve_id`.

### 5.4 `templates/npm__minimatch__CVE-2022-3517.py`

See §8 (vertical slice) for full rationale. The template produces a `PocPlan` with:
- `files`: `{"trigger.js": <guard-presence probe>, "package.json": <stub>}` — feeds a 70000-char
  pattern (`"a".repeat(70000)`, exceeding `MAX_PATTERN_LENGTH=65536` introduced by the 3.0.5 fix)
  to `minimatch()`. minimatch 3.0.5 throws via `assertValidPattern` (length guard) → emits
  `PATCHED` + `exit 1`; minimatch 3.0.4 has no guard → reaches match silently → emits
  `VULN_CONFIRMED` + `exit 0`. Only the two constant sentinels reach stdout; the TypeError
  message goes to stderr. A stub `package.json` is included so `npm install --no-save` and
  `require("minimatch")` resolve deterministically in the workdir.
- `install_cmd`: `["npm", "install", "--no-save", f"minimatch@{version}"]` (pinned from seed).
- `install_hosts`: `["registry.npmjs.org"]`.
- `expected_trigger_exit`: `0`.
- `expected_trigger_sha256`: `sha256("VULN_CONFIRMED\n")` — derived offline from `SENTINEL_CONFIRMED`.
- Empirical validation (3.0.4 → VULN_CONFIRMED, 3.0.5 → PATCHED) pending a docker-capable run.

### 5.5 `llm_strategy.py`

```python
class LLMPocStrategy:
    def supports(self, hypothesis: dict) -> bool:
        return False  # not wired in v1

    def build_plan(self, hypothesis: dict) -> PocPlan:
        raise NotImplementedError(
            "LLMPocStrategy is a defined seam only; wire via select_strategy('llm') "
            "after implementing LLM-backed PoC generation."
        )
```

This is a deliberate, reviewable commit of the seam decision. `select_strategy` dispatches to
it only when `SECRESEARCH_POC_STRATEGY=llm`; the default is `"templated"`.

### 5.6 `harness.py`

**`verify_hypotheses(hypotheses, slug, *, strategy=None) -> list[dict]`**

```
strategy = strategy or select_strategy()
for hyp in hypotheses:
    hypothesis_id = hyp["hypothesis_id"]
    try:
        if not strategy.supports(hyp):
            append verify-no-strategy ledger event
            verdicts.append(Verdict(..., verdict=SKIPPED, reason="no-strategy"))
            continue
        plan = strategy.build_plan(hyp)              # raises SeedIncomplete if seed bad
    except SeedIncomplete as e:
        append verify-seed-incomplete ledger event
        verdicts.append(Verdict(..., verdict=SKIPPED, reason=str(e)))
        continue
    except SandboxError as e:                        # build_plan itself shouldn't call sandbox
        append verify-sandbox-error ledger event     # but catch defensively
        verdicts.append(Verdict(..., verdict=ERROR, reason=str(e)))
        continue
    # ScopeViolation from _drive_phased propagates uncaught (C1)
    try:
        install_ev, trigger_ev = _drive_phased(plan, hypothesis_id, slug)
    except SandboxError as e:
        append verify-sandbox-error ledger event
        verdicts.append(Verdict(..., verdict=ERROR, reason=str(e)))
        continue
    verdict_str = derive_verdict(trigger_ev, plan)
    v = Verdict(hypothesis_id=hypothesis_id, ..., verdict=verdict_str, ...)
    append verify-verdict ledger event
    verdicts.append(v)
_persist(verdicts, slug)
return [asdict(v) | {"verified": v.verdict == VERDICT_VERIFIED} for v in verdicts]
```

**`_drive_phased(plan, hypothesis_id, slug) -> tuple[EvidenceCapture, EvidenceCapture]`**

```
W = RUNTIME_VERDICTS_DIR / slug / "work" / hypothesis_id
W.mkdir(parents=True, exist_ok=True)
for name, content in plan.files.items():
    (W / name).write_text(content, encoding="utf-8")

install_result = sandbox_run(
    plan.install_cmd,
    ecosystem=plan.ecosystem,
    phase="install",
    workdir_host=W,
    timeout=INSTALL_TIMEOUT,
    network_allow=plan.install_hosts,
)
install_ev = EvidenceCapture(phase="install", exit_code=install_result.exit_code,
                             stdout_sha256=install_result.stdout_sha256,
                             timed_out=install_result.timed_out,
                             duration_s=install_result.duration_s)
if install_result.exit_code != 0 or install_result.timed_out:
    raise SandboxError(f"install phase failed: exit={install_result.exit_code} "
                       f"timed_out={install_result.timed_out}")

trigger_result = sandbox_run(
    plan.trigger_cmd,
    ecosystem=plan.ecosystem,
    phase="execute",          # --network none (C2)
    workdir_host=W,
    timeout=TRIGGER_TIMEOUT,
)
trigger_ev = EvidenceCapture(phase="trigger", ...)
return install_ev, trigger_ev
```

The shared `W` (bind-mounted host workdir) is the install→trigger handoff channel: install
writes `node_modules/`, trigger reads it. Containers are `--rm`; the host workdir is the only
persistent surface.

**`_persist(verdicts, slug)`**

Writes `runtime/verdicts/<slug>/verdicts.json` (full `asdict` list). Writes raw stdout to
`runtime/verdicts/<slug>/evidence/<hypothesis_id>/{install,trigger}.stdout.txt` (gitignored).
Mirrors the grouped-by-slug pattern from `scripts/llm/generate.py:48-103`.

**Ledger events** (via `ledger.append_event`):
- `verify-started` — once per `verify_hypotheses` call.
- `verify-no-strategy` — per hypothesis skipped for no matching strategy.
- `verify-seed-incomplete` — per hypothesis skipped for missing seed fields.
- `verify-sandbox-error` — per hypothesis that hits `SandboxError`.
- `verify-verdict` — per hypothesis that reaches a final verdict (verified/refuted/error).
- (Plus two `sandbox-exec` events 4a appends per container — already handled by runner.py.)

---

## 6. Error handling

| Condition | Response | Verdict |
|-----------|----------|---------|
| Strategy has no template for hypothesis | `verify-no-strategy` ledger; continue | `skipped` |
| `evidence_seed` fields missing or blank | `SeedIncomplete`; `verify-seed-incomplete` ledger; continue | `skipped` |
| Install phase exit ≠ 0 or timed_out | `SandboxError` raised by `_drive_phased`; caught in `verify_hypotheses`; `verify-sandbox-error` ledger; continue | `error` |
| Trigger timed out | `trigger.timed_out=True`; `derive_verdict` → `error` | `error` |
| Docker unreachable (`SandboxError` from `sandbox_run`) | caught per-item; `verify-sandbox-error` ledger; continue | `error` |
| `ScopeViolation` (install-phase host out of scope) | propagates **uncaught** from `_drive_phased` through `verify_hypotheses` → caller → CLI exit 1 | (batch aborts) |
| Trigger exit/sha mismatch | `derive_verdict` → `refuted`; `reason` records actual-vs-expected | `refuted` |
| Persist I/O failure | logged; batch result still returned (best-effort persist) | (verdicts still returned) |

---

## 7. Testing strategy

Offline, TDD, mirroring the Stage 4a / 4b patterns (injected runner, failing test →
implement → full suite green → commit per task).

**Unit (default, no docker):**

- `test_verify_model.py` — `Verdict` / `EvidenceCapture` construction, `derive_verdict` all
  four verdict paths (verified, refuted, timed_out→error, mismatch→refuted).
- `test_verify_strategy.py` — `select_strategy` dispatch (env override, default templated,
  unknown → ValueError), `PocStrategy` is `runtime_checkable` (isinstance check against a
  duck-type), `SeedIncomplete` is `ValueError`.
- `test_verify_templated.py` — `TemplatedPocStrategy.supports` true/false, `build_plan` shape
  (returns `PocPlan` with correct fields), `SeedIncomplete` raised on missing fields.
- `test_verify_harness_drive.py` — `_drive_phased`: phase ordering install→trigger, trigger
  uses `phase="execute"` (asserted against injected runner argv), shared workdir, install
  failure → `SandboxError` (trigger not called), `EvidenceCapture` shape.
- `test_verify_harness.py` — `verify_hypotheses`: `verified`/`refuted`/`error`/`skipped`
  verdicts, `SandboxError` per-item isolation (one error does not kill the batch),
  `ScopeViolation` propagates uncaught (batch-aborts), ledger events fired per path,
  `"verified"` bool key present on every returned dict.
- `test_verify_persist.py` — `_persist`: slug-grouped layout, `verdicts.json` written and
  parseable, evidence stdout files present.
- `test_nightly_stage_verify.py` — `nightly.stage_verify` calls `verify_hypotheses`;
  `stage_briefing` counter still reads the `"verified"` key.

**Docker-gated live test** (`tests/scripts/test_verify_live.py`):
```python
@pytest.mark.skipif(
    not _docker_available() or os.environ.get("VERIFY_LIVE") != "1",
    reason="requires docker in WSL2 + VERIFY_LIVE=1"
)
def test_minimatch_304_verified_305_refuted(tmp_path): ...
```
`minimatch@3.0.4` → verdict `"verified"`; `minimatch@3.0.5` → verdict `"refuted"`. Confirms
the Task-3 pinned `expected_trigger_sha256` against a real container. Run:
`VERIFY_LIVE=1 python -m pytest tests/scripts/test_verify_live.py -q` (requires
`python scripts/sandbox/doctor.py` first).

**Full offline suite:** `cd sec-research && python -m pytest -q` — green, new `test_verify_*`
covered, count grows monotonically. Baseline before Task 0: confirm with `pytest --co -q |
wc -l`.

---

## 8. Vertical slice: dependency-cve / minimatch guard-presence probe

**The planned slice:** npm `minimatch@3.0.4`, CVE-2022-3517 —
GHSA-f8q6-p94x-37v3 (affected: < 3.0.5; fixed: 3.0.5, commit a8763f4).

**Why this slice:**
- Trigger is pure-computational, zero additional dependencies, no network at trigger time.
- Success collapses to a **constant sentinel + exit code**: deterministic guard-presence probe
  (see below). Variable output never enters stdout. Therefore
  `expected_trigger_sha256 = sha256("VULN_CONFIRMED\n")` is stable across runs and machines.
- The `3.0.4` → `verified` / `3.0.5` → `refuted` version boundary proves the harness produces
  *both* verdicts, not a rubber stamp.
- npm + `npm_config_ignore_scripts=true` (`_images.py:16`) means the fetched package's
  lifecycle scripts don't run; only our `trigger.js` executes, airgapped.

**Anti-fabrication gate (PT-4 / CLAUDE.md):**
> The exact CVE↔affected↔fixed triplet (CVE-2022-3517 / GHSA-f8q6-p94x-37v3 /
> affected 3.0.4 / fixed 3.0.5) is stated here as the **planned** slice based on
> public advisory records. It MUST be confirmed against osv.dev/GHSA at Task-3
> implementation time before pinning `expected_trigger_sha256`. If the precise
> triplet differs from what osv.dev returns, the template *structure* is unchanged
> but the pinned version and hash are updated to match verified reality.

**Guard-presence probe mechanism (v1 deterministic signal):**
The 3.0.5 fix (commit a8763f4) introduced `MAX_PATTERN_LENGTH = 1024*64` (65536) and
`assertValidPattern(pattern)` that throws `TypeError('pattern is too long')` at the top of
`minimatch()` when `pattern.length > 65536`. The `trigger.js` feeds a 70000-char pattern:

```javascript
const OVERLONG = "a".repeat(70000); // > MAX_PATTERN_LENGTH (65536)
let threw = false;
try {
  minimatch("probe-target", OVERLONG);
} catch (e) {
  threw = true;
  process.stderr.write("length guard present (patched): " + e.message + "\n");
}
if (!threw) {
  process.stdout.write("VULN_CONFIRMED\n");  // no length guard -> affected -> verified
  process.exit(0);
} else {
  process.stdout.write("PATCHED\n");          // guard present -> fixed -> refuted
  process.exit(1);
}
```

- minimatch 3.0.4: no length guard → reaches match silently → `VULN_CONFIRMED\n` + `exit 0` → **verified**
- minimatch 3.0.5: `assertValidPattern` throws → `PATCHED\n` + `exit 1` → **refuted**

This is the deterministic v1 signal: confirms the resolved version lacks the 3.0.5
DoS-mitigation guard. True ReDoS detonation (timing-based backtracking) is deferred to a
future template version; this probe is sufficient and fully reproducible.

**Empirical validation pending a docker-capable run** (VERIFY_LIVE=1 gate). The offline suite
confirms the Python/JS sentinel contract; docker confirms real minimatch behavior.

---

## 9. Out of scope (this sub-project)

- Finding markdown / `findings/<trace>/` drafting (Stage 6 `stage_draft_findings`) — 4c emits
  verdicts only; Stage 6 is untouched.
- LLM-backed `PocStrategy` (breadth beyond constant-signal exploits) — requires a
  `deterministic: bool` flag and sanitized-capture relaxation that would weaken the v1 sha256
  guarantee; deliberately deferred behind the `LLMPocStrategy` seam.
- Non-{npm} ecosystems in v1 (pypi/cargo/rubygems templates are a follow-up; the harness
  architecture supports them via `TEMPLATE_REGISTRY`).
- Any `schema/*.json` modification — Stage-1 locked.
- Non-deterministic-output exploit classes (timing side-channels, secrets extraction,
  address-space probing) — these require the sanitized-capture relaxation deferred to the
  LLM seam.
- `hb-anc` — deferred 4b minors including authoring the missing 4b spec doc; not addressed
  here.

---

## 10. References

- `docs/CHARTER.md` — §Stages (4c closes the hypothesis→evidence gap).
- `docs/HOOK_CONTRACTS.md` — PT-5 (sandbox), PT-4 (anti-fabrication), G-1/G-4 (commit gates).
- `docs/EVIDENCE_DISCIPLINE.md` — PoC + evidence requirements.
- `docs/superpowers/specs/2026-06-22-stage4a-sandbox-design.md` — 4a sandbox design (Predecessor).
- `docs/superpowers/plans/2026-06-22-stage4a-sandbox.md` — 4a implementation plan.
- `schema/hypothesis.schema.json:40-43` — evidence_seed delegation to 4c.
- `schema/finding.schema.json` — immutable finding contract (not modified).
- `hooks/lib/policy.py` — `check_http` / `ScopeViolation` / `is_in_scope`.
- `hooks/lib/ledger.py:46` — `append_event(...)`.
- `scripts/sandbox/runner.py:77` — `sandbox_run` (reused as-is).
- `scripts/llm/generate.py:48-103` — per-item isolation + persist patterns to mirror.
- `scripts/llm/client.py:31-48` — Protocol + `select_*()` dispatch shape to mirror.

---

## 11. History

| Date | Change |
|------|--------|
| 2026-06-22 | Initial design. Decisions locked in brainstorm: PoC authoring = Hybrid (templated v1 + LLM seam behind Protocol); verification depth = full exploit reproduction; constant-sentinel constraint bounds v1 template scope; `scripts/verify/` package mirrors `scripts/sandbox/` / `scripts/llm/`; `ScopeViolation` propagates uncaught; install→trigger shared-workdir handoff; `runtime/verdicts/` layout; `nightly.stage_verify` is the only existing file modified. Vertical slice: npm minimatch ReDoS (CVE-2022-3517 / GHSA-f8q6-p94x-37v3) — triplet to be confirmed against osv.dev at Task-3 time. |
| 2026-06-22 | C-1 correction: replaced timing/brace-expansion approach with deterministic guard-presence probe grounded in the real 3.0.5 fix commit (a8763f4). New mechanism feeds a 70000-char pattern; 3.0.5 throws via `assertValidPattern` (MAX_PATTERN_LENGTH=65536) → PATCHED → refuted; 3.0.4 has no guard → VULN_CONFIRMED → verified. Sentinel updated from `REDOS_CONFIRMED` → `VULN_CONFIRMED`; stub `package.json` added to plan.files (I-1); `target_identifier` now includes version (I-2); lowercase-ecosystem registry assumption documented (T3). Empirical validation pending docker-capable run. |
