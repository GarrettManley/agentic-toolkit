# Handoff

## State

**Stage 4c — sandboxed verification harness SHIPPED to master, offline-green** (tracker
**hb-s2c**). This is the hypothesis→evidence bridge of the sec-research bug-bounty pipeline:
it turns Stage-4b hypotheses into per-hypothesis PoCs, runs them through the Stage-4a sandbox
with a **phased install→trigger split**, and emits **verified/refuted/skipped/error** verdicts,
filling the `nightly.stage_verify` stub.

Built via brainstorming → writing-plans → subagent-driven TDD (9 tasks, fresh implementer +
reviewer per task) → final whole-branch review (opus) → one fix wave → re-review clean.
- **11 commits on master**, `d044ca8..0f8ac2f`. **294 passed / 3 skipped** (controller-verified).
- Plan: `~/.claude/plans/writing-plans-brainstorming-workflows-l-goofy-pnueli.md`.
- SDD ledger (full task-by-task record + every decision): `sec-research/.superpowers/sdd/progress.md`.
- Spec: `docs/superpowers/specs/2026-06-22-stage4c-verify-design.md`; plan doc `docs/superpowers/plans/2026-06-22-stage4c-verify.md`.

New package `scripts/verify/`:
- `model.py` — `EvidenceCapture`, `Verdict` frozen dataclasses, `VERDICT_*`, pure `derive_verdict`.
- `strategy.py` — `PocPlan`, `@runtime_checkable PocStrategy` Protocol, `SeedIncomplete`,
  `select_strategy` (env `SECRESEARCH_POC_STRATEGY`, default `templated`).
- `templated.py` + `templates/npm__minimatch__CVE_2022_3517.py` — deterministic exploit-template
  strategy; v1 slice = npm minimatch ReDoS (CVE-2022-3517, affected <3.0.5, fixed 3.0.5).
- `llm_strategy.py` — defined-but-not-wired LLM seam (`supports()→False`, `build_plan()→NotImplementedError`).
- `harness.py` — `_drive_phased` (two-phase), `verify_hypotheses` (orchestrator), `_persist` →
  `runtime/verdicts/<slug>/verdicts.json`.
- `nightly.stage_verify` wired to `verify_hypotheses`. Reuses Stage-4a `sandbox.runner.sandbox_run` as-is.

## Next
1. **hb-ctr (P2) — VALIDATE the verify template on a docker host. THE merge gate.** The one
   exploit template was NEVER run against a real container (no docker in WSL2). Install docker
   in WSL2, then: `cd sec-research && python scripts/sandbox/doctor.py` then
   `VERIFY_LIVE=1 python -m pytest tests/scripts/test_verify_live.py -q`. Expect minimatch@3.0.4
   → `verified`, @3.0.5 → `refuted`. **Until this passes, do NOT trust live `verified` verdicts.**
2. Then close **hb-s2c**.
3. Deferred minors (final-review triage, all non-blocking): a couple of unused-`monkeypatch`
   test params, one near-duplicate test, one missing test-helper return annotation. Optional cleanup pass.
4. **hb-anc (P3)** — deferred Stage-4b minors incl. the missing 4b spec doc.

## Don't retry / gotchas
- **The verify mechanism is a guard-presence probe, NOT ReDoS detonation** (user decision this
  session). trigger.js feeds a >64KB pattern: minimatch 3.0.5 throws via its `assertValidPattern`
  length guard (MAX_PATTERN_LENGTH=65536, added in fix commit `a8763f4`) → `PATCHED` → refuted;
  3.0.4 lacks the guard → `VULN_CONFIRMED` → verified. The earlier template used balanced
  `{a,b}` brace-expansion — WRONG mechanism (present in both versions); the final review caught
  it (C-1). Don't revert to a brace/timing approach without re-validating.
- **Determinism is load-bearing:** only constant sentinels reach stdout (errors → stderr);
  `expected_trigger_sha256 = sha256("VULN_CONFIRMED\n")`, computed offline, invariant across
  machines. Don't let variable data (timings, error text) into stdout.
- **ScopeViolation must propagate UNCAUGHT** through `verify_hypotheses` (it's `Exception`, not
  `SandboxError`; carries a policy-blocked audit side-effect). Only `SeedIncomplete`/`SandboxError`
  are caught per-item. No `except Exception` anywhere.
- **EvidenceCapture carries `stdout_sha256`, not raw stdout** — so v1 persists `verdicts.json`
  only (no raw-stdout evidence files; the spec's earlier mention of those is superseded).
- **Verify counts yourself** — re-run `pytest`; two prior sessions' implementer reports mis-stated
  arithmetic. Controller confirmed 294/3 directly.
- Commits land directly on master (matches 4a/4b); sec-research G-1..G-4 apply per commit
  (4c writes nothing to `findings/`, so G-1/G-4 are no-ops; G-2 secret-scan runs). `.superpowers/`
  is gitignored scratch.

## Context
- Full offline suite: `cd sec-research && python -m pytest -q` (294 passed / 2-3 skipped; the
  live test skips without docker+VERIFY_LIVE).
- Verdicts persist to `runtime/verdicts/<slug>/verdicts.json` (gitignored).
- Beads: `bd -C ~/.claude/harness-backlog show hb-ctr` (next gate), `hb-s2c` (this work), `hb-anc` (4b follow-ups).
