# Stage 4c — Sandboxed Verification Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `scripts/verify/` package so each hypothesis emitted by Stage 4b is turned into a two-phase sandboxed PoC (install → trigger), executed through the Stage-4a `sandbox_run` chokepoint, and emitted as a typed verdict (`verified / refuted / skipped / error`) persisted to `runtime/verdicts/<slug>/`. Wire `nightly.stage_verify` to use it.

**Architecture:** A `PocStrategy` Protocol abstracts PoC authoring; a `TemplatedPocStrategy` ships in v1 with one real exploit template (npm minimatch ReDoS); `verify_hypotheses` drives the harness per-hypothesis with per-item `SandboxError` isolation; the trigger phase is always `--network none`; `ScopeViolation` propagates uncaught. Full rationale and interface contracts: `docs/superpowers/specs/2026-06-22-stage4c-verify-design.md`.

**Tech Stack:** Python 3.14, `sandbox_run` (`wsl -e docker` via Stage 4a), stdlib only (`subprocess`, `hashlib`, `json`, `pathlib`, `dataclasses`), `pytest`. All unit tests offline via injected runner; one docker-gated live test auto-skips.

**Tracking:** `hb-s2c` (Follows up hb-oec). Spec: `docs/superpowers/specs/2026-06-22-stage4c-verify-design.md`.

## Global Constraints

- **Working directory:** all commands run from inside `sec-research/`. Commits stage **only** `sec-research/` paths.
- **Stage 1 is the contract:** do NOT modify `schema/*.json`, any hook, `hooks/lib/policy.py`, or `hooks/lib/ledger.py`. New `scripts/verify/` package + new tests are additive. The ONLY existing file modified is `scripts/nightly.py` (the `stage_verify` stub rewire).
- **`ScopeViolation` propagates uncaught (C1):** never wrap the install `sandbox_run` in a handler that catches `ScopeViolation`. Catch only `SandboxError` and `SeedIncomplete` per item.
- **Trigger is `--network none` (C2):** asserted in tests against the constructed argv. No exceptions.
- **Fail-closed (C3):** docker unreachable → all verdicts are `error`; never `verified`; no host fallback.
- **No schema changes (C4):** `schema/*.json` is Stage-1 locked.
- **Verdicts only (C5):** no `findings/<trace>/` directory, no Trace-ID, no finding.md. Stage 6 owns finding creation.
- **Per-item isolation (C6):** `SandboxError` per item → `error` verdict + ledger + continue. One failure never kills the batch.
- **Do NOT reuse `scripts/verify_finding.py:66` `run_poc_in_sandbox`:** that is single-pass `phase="install"` for the immutable finding contract. Call `sandbox_run` directly for the two-phase split.
- **TDD, frequent commits, DRY, YAGNI.** Run `pytest` before every commit. Verify test count grows monotonically — do not trust implementer arithmetic.

---

## File Structure

**Create:**
- `scripts/verify/__init__.py` — package marker (empty).
- `scripts/verify/model.py` — `EvidenceCapture`, `Verdict`, `VERDICT_*` constants, `derive_verdict`.
- `scripts/verify/strategy.py` — `PocPlan`, `PocStrategy` Protocol, `SeedIncomplete`, `select_strategy`.
- `scripts/verify/llm_strategy.py` — `LLMPocStrategy` stub (seam only; `supports()→False`).
- `scripts/verify/templated.py` — `TemplatedPocStrategy` + `TEMPLATE_REGISTRY`.
- `scripts/verify/templates/npm__minimatch__CVE-2022-3517.py` — vertical-slice exploit template.
- `scripts/verify/harness.py` — `verify_hypotheses`, `_drive_phased`, `_persist`, `RUNTIME_VERDICTS_DIR`.
- `tests/scripts/test_verify_model.py`, `test_verify_strategy.py`, `test_verify_templated.py`, `test_verify_harness_drive.py`, `test_verify_harness.py`, `test_verify_persist.py`, `test_nightly_stage_verify.py`.
- `tests/scripts/test_verify_live.py` — docker-gated live test.

**Modify:**
- `scripts/nightly.py` — replace `stage_verify` stub with `verify.harness.verify_hypotheses` call.

**Available from conftest (Stage 2):** `tests/conftest.py` puts `scripts/` and `hooks/` on `sys.path`, so `from verify.harness import verify_hypotheses` and `from sandbox.runner import sandbox_run` resolve in tests.

---

## Task 0: Spec + plan docs

- [x] Write `docs/superpowers/specs/2026-06-22-stage4c-verify-design.md` (this spec).
- [x] Write `docs/superpowers/plans/2026-06-22-stage4c-verify.md` (this plan).
- [ ] Review spec for completeness against the approved plan before Task 1. No code.

---

## Task 1: `model.py` + `strategy.py`

**Files:**
- Create: `scripts/verify/__init__.py` (empty)
- Create: `scripts/verify/model.py`
- Create: `scripts/verify/strategy.py`
- Create: `tests/scripts/test_verify_model.py`, `tests/scripts/test_verify_strategy.py`

**Interfaces produced:**
- `EvidenceCapture(phase, exit_code, stdout_sha256, timed_out, duration_s)` frozen dataclass.
- `Verdict(hypothesis_id, program_slug, target_identifier, vuln_class, verdict, reason, strategy, template_id, evidence, verified_at)` frozen dataclass.
- `VERDICT_VERIFIED`, `VERDICT_REFUTED`, `VERDICT_SKIPPED`, `VERDICT_ERROR` string constants.
- `derive_verdict(trigger: EvidenceCapture, plan: PocPlan) -> str` pure function.
- `PocPlan(files, install_cmd, install_hosts, trigger_cmd, expected_trigger_exit, expected_trigger_sha256, ecosystem)` dataclass.
- `PocStrategy(@runtime_checkable Protocol)` with `supports(hyp) -> bool` and `build_plan(hyp) -> PocPlan`.
- `SeedIncomplete(ValueError)`.
- `select_strategy(name=None) -> PocStrategy` (env `SECRESEARCH_POC_STRATEGY`, default `"templated"`).

**Tests to write (failing first):**

`test_verify_model.py`: `derive_verdict` → verified (exact match), refuted (sha mismatch), refuted (exit mismatch), error (timed_out). `Verdict` and `EvidenceCapture` construct and are frozen.

`test_verify_strategy.py`: `select_strategy()` returns `TemplatedPocStrategy` by default; env `SECRESEARCH_POC_STRATEGY=llm` returns `LLMPocStrategy`; unknown name → `ValueError`. `PocStrategy` is `runtime_checkable` — a duck-typed object passing `isinstance(obj, PocStrategy)`. `SeedIncomplete` is a `ValueError`.

- [ ] Write failing tests.
- [ ] Run to verify failure (`No module named 'verify'`).
- [ ] Implement `__init__.py`, `model.py`, `strategy.py` (stub imports for `TemplatedPocStrategy`/`LLMPocStrategy` until Task 3/2).
- [ ] Run tests to verify they pass.
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Commit: `feat(verify): verdict model + PocStrategy Protocol + select_strategy dispatch`

---

## Task 2: `llm_strategy.py` stub

**Files:**
- Create: `scripts/verify/llm_strategy.py`

**Interfaces produced:** `LLMPocStrategy` — `supports()→False`, `build_plan()→NotImplementedError`.

This is a deliberate, reviewable commit of the seam decision. No tests required beyond the `select_strategy` dispatch already tested in Task 1.

- [ ] Implement `llm_strategy.py` (the 10-line seam; see spec §5.5).
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Commit: `feat(verify): LLMPocStrategy seam stub — defined behind Protocol, not wired`

---

## Task 3: `templated.py` + minimatch template + registry

**Files:**
- Create: `scripts/verify/templated.py`
- Create: `scripts/verify/templates/__init__.py` (empty)
- Create: `scripts/verify/templates/npm__minimatch__CVE-2022-3517.py`
- Create: `tests/scripts/test_verify_templated.py`

**Pre-implementation gate (anti-fabrication):** Before writing the template, confirm the CVE↔affected↔fixed triplet against osv.dev/GHSA:
```
GET https://api.osv.dev/v1/vulns/GHSA-f8q6-p94x-37v3
```
Verify: `affected[].package.name == "minimatch"`, affected range includes `3.0.4`, first fixed version is `3.0.5`. If the triplet differs, update template accordingly. Record the confirmation in the commit message.

**Interfaces produced:** `TemplatedPocStrategy` implementing `PocStrategy`; `TEMPLATE_REGISTRY` with the minimatch entry; `build_plan` produces a correct `PocPlan`.

**Tests to write:**

`test_verify_templated.py`: `supports` returns True for a hypothesis with the minimatch seed triple; False for an unregistered triple. `build_plan` returns a `PocPlan` with non-empty `files`, non-empty `install_cmd`, non-empty `trigger_cmd`, `ecosystem=="npm"`, numeric `expected_trigger_exit`, non-empty `expected_trigger_sha256`. `SeedIncomplete` raised when any required field (`package_ecosystem`, `package_name`, `affected_versions_range`, `candidate_cve_id`) is absent or blank.

- [ ] Confirm CVE triplet against osv.dev (REQUIRED — do not skip).
- [ ] Write failing tests.
- [ ] Run to verify failure.
- [ ] Implement `templated.py` + template (with confirmed sha256 pinned for `minimatch@3.0.4`).
- [ ] Run tests to verify they pass.
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Commit: `feat(verify): TemplatedPocStrategy + minimatch@3.0.4 ReDoS template (CVE-2022-3517 triplet confirmed)`

---

## Task 4: `harness._drive_phased`

**Files:**
- Create: `scripts/verify/harness.py` (partial — `_drive_phased` + `RUNTIME_VERDICTS_DIR` only)
- Create: `tests/scripts/test_verify_harness_drive.py`

**Interfaces produced:** `_drive_phased(plan, hypothesis_id, slug, *, runner=sandbox_run) -> tuple[EvidenceCapture, EvidenceCapture]` (injectable runner for tests). `RUNTIME_VERDICTS_DIR`.

**Tests to write:**

`test_verify_harness_drive.py`: phase ordering — install is called before trigger; trigger argv contains `phase="execute"` (`--network none` asserted against injected runner); both phases receive the same `workdir_host`; `plan.files` are materialized into the workdir before the install call; install failure (exit ≠ 0) → `SandboxError` raised, trigger runner never called; `EvidenceCapture` shape matches `SandboxResult` fields.

- [ ] Write failing tests.
- [ ] Run to verify failure.
- [ ] Implement `_drive_phased` and `RUNTIME_VERDICTS_DIR` in `harness.py`.
- [ ] Run tests to verify they pass.
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Commit: `feat(verify): harness._drive_phased install→trigger phased execution`

---

## Task 5: `harness.verify_hypotheses`

**Files:**
- Extend: `scripts/verify/harness.py` (add `verify_hypotheses`)
- Create: `tests/scripts/test_verify_harness.py`

**Interfaces produced:** `verify_hypotheses(hypotheses, slug, *, strategy=None) -> list[dict]`.

**Tests to write:**

`test_verify_harness.py`:
- verified path: `derive_verdict` returns `VERDICT_VERIFIED`; returned dict has `"verified": True`.
- refuted path: `derive_verdict` returns `VERDICT_REFUTED`; returned dict has `"verified": False`.
- error path (SandboxError from _drive_phased): verdict is `VERDICT_ERROR`; batch continues (next item processed).
- skipped path (no strategy): verdict is `VERDICT_SKIPPED`; `verify-no-strategy` ledger event fired.
- skipped path (SeedIncomplete): verdict is `VERDICT_SKIPPED`; `verify-seed-incomplete` ledger event fired.
- ScopeViolation propagates uncaught out of `verify_hypotheses` (asserted with `pytest.raises`).
- ledger events: `verify-started` fires once; `verify-verdict` fires per verdict-reaching hypothesis.
- `"verified"` bool key present on every dict in the returned list.

- [ ] Write failing tests.
- [ ] Run to verify failure.
- [ ] Implement `verify_hypotheses` in `harness.py`.
- [ ] Run tests to verify they pass.
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Commit: `feat(verify): verify_hypotheses orchestrator + per-item isolation + verdict derivation`

---

## Task 6: `_persist` to `runtime/verdicts/`

**Files:**
- Extend: `scripts/verify/harness.py` (add `_persist` + evidence file writes)
- Create: `tests/scripts/test_verify_persist.py`

**Interfaces produced:** `_persist(verdicts: list[Verdict], slug: str, *, evidence: dict[str, tuple[SandboxResult, SandboxResult]]) -> None`.

**Tests to write:**

`test_verify_persist.py`: `runtime/verdicts/<slug>/verdicts.json` written and parseable JSON array; each element has all `Verdict` fields + `"verified"` bool; `runtime/verdicts/<slug>/evidence/<hypothesis_id>/install.stdout.txt` and `trigger.stdout.txt` written with the raw stdout strings; calling `_persist` twice (idempotent re-run) overwrites rather than appends `verdicts.json`.

- [ ] Write failing tests.
- [ ] Run to verify failure.
- [ ] Implement `_persist` (and wire it into `verify_hypotheses`).
- [ ] Run tests to verify they pass.
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Commit: `feat(verify): _persist verdicts.json + evidence stdout files`

---

## Task 7: Wire `nightly.stage_verify`

**Files:**
- Modify: `scripts/nightly.py` (the `stage_verify` stub)
- Create: `tests/scripts/test_nightly_stage_verify.py`

**Change:** Replace the stub with:
```python
from verify.harness import verify_hypotheses
# in stage_verify:
return verify_hypotheses(hypotheses, slug)
```
The returned `list[dict]` already carries `"verified": bool`, so `stage_briefing`'s counter
at `nightly.py:102` (`sum(v["verified"] for v in verdicts)`) needs no change.

**Tests to write:**

`test_nightly_stage_verify.py`: `nightly.stage_verify` calls `verify_hypotheses` (monkeypatched); the result is passed through unchanged; `stage_briefing` counter reads `"verified"` from the dict (regression guard — counter still works after the wire).

- [ ] Read `scripts/nightly.py`'s `stage_verify` stub before touching it.
- [ ] Write failing tests.
- [ ] Run to verify failure.
- [ ] Implement the wire.
- [ ] Run tests to verify they pass.
- [ ] Run full suite: `python -m pytest -q`. All green.
- [ ] Pipeline smoke: `python scripts/nightly.py` with the minimatch hypothesis in `runtime/hypotheses/<slug>/` → briefing shows a `verified` count; `runtime/verdicts/<slug>/verdicts.json` written.
- [ ] Commit: `feat(verify): wire nightly.stage_verify to verify_hypotheses`

---

## Task 8: Docker-gated live test

**Files:**
- Create: `tests/scripts/test_verify_live.py`

**Test:**
```python
@pytest.mark.skipif(
    not _docker_available() or os.environ.get("VERIFY_LIVE") != "1",
    reason="requires docker in WSL2 + VERIFY_LIVE=1"
)
def test_minimatch_304_verified_305_refuted(tmp_path):
    # minimatch@3.0.4 hypothesis → verdict "verified"
    # minimatch@3.0.5 hypothesis → verdict "refuted"
    ...
```

Run: `python scripts/sandbox/doctor.py` first to confirm docker + images ready.
Run: `VERIFY_LIVE=1 python -m pytest tests/scripts/test_verify_live.py -q`.

This test confirms the Task-3 pinned `expected_trigger_sha256` against a real container and
proves the harness produces both verdicts from real packages.

- [ ] Write the live test (skips in normal CI; requires `VERIFY_LIVE=1`).
- [ ] Run full offline suite: `python -m pytest -q`. All green (live test skipped).
- [ ] Run live test (opt-in): `VERIFY_LIVE=1 python -m pytest tests/scripts/test_verify_live.py -q`. Passes.
- [ ] Commit: `feat(verify): docker-gated live test minimatch@3.0.4→verified + 3.0.5→refuted`

---

## Verification

**1. Full offline suite (every commit):**
```powershell
cd C:\Users\Garre\Workspace\sec-research
python -m pytest -q
```
Expected: all green; new `test_verify_*` covered; count grows monotonically. Verify the
number yourself — do not trust implementer arithmetic (a 4b-session gotcha).

**2. Live exploit reproduction (opt-in, requires docker):**
```powershell
python scripts/sandbox/doctor.py                          # confirm sandbox ready
VERIFY_LIVE=1 python -m pytest tests/scripts/test_verify_live.py -q
```

**3. Pipeline smoke:**
```powershell
python scripts/nightly.py
```
With a minimatch hypothesis in `runtime/hypotheses/<slug>/`: briefing shows a `verified`
count; `runtime/verdicts/<slug>/verdicts.json` written.

**4. Commit gates:** sec-research G-1..G-4 apply per commit. 4c writes nothing to `findings/`
so G-1/G-4 are no-ops. G-2 secret-scan still runs. Workspace-root verify gate skips
sec-research-only commits.

---

## Retrospective

**Issue state:** Closes hb-s2c (Stage 4c sandboxed verification harness). Follows up hb-anc
(deferred 4b minors including the missing 4b spec doc; not addressed here).

- **What worked:**
- **Friction / surprises:**
- **Constant-sentinel determinism** (did the minimatch watchdog hold across runs? was the threshold right?):
- **Install→trigger shared-workdir handoff** (did the bind-mounted `W` survive the `--rm` container lifecycle on WSL2?):
- **Verdict taxonomy** (was `verified/refuted/skipped/error` sufficient or did real hypotheses need more states?):
- **Per-item `SandboxError` isolation** (did it work end-to-end without killing the batch?):
- **4a `sandbox_run` seam** (pure reuse, or did it need extension?):
- **Follow-ups discovered:**
