# Adversarial Plan Review — First Real Run (sec-research × huntr.com)

**Plan reviewed:** `docs/superpowers/specs/2026-06-27-first-real-run-huntr-design.md`
**Date:** 2026-06-27
**Agents:** 6 dimensions (feasibility, value-justification, clarity, completeness, risk-rollback, scope-cut) + 3 archetypes (plan-skeptic, plan-feasibility-auditor, plan-scope-cutter)
**Verdict: NO-GO as written.** A premise-breaking capability gap makes both done-criteria unreachable. Material rework required before this becomes an implementation plan.

---

## CRITICAL

```
[CRITICAL] — §3 / §1.1 "the only new build is hb-be9; everything else exercises existing code" → FALSE. verify/llm_strategy.py.build_plan() raises NotImplementedError and LLMPocStrategy.supports() returns False; verify/templated.py TEMPLATE_REGISTRY has exactly ONE entry (npm/minimatch/CVE-2022-3517). The novel-PoC-authoring capability is unimplemented — that, not hb-be9, is the load-bearing prerequisite.
[CRITICAL] — §1.3(a) draft path → Structurally unreachable. Any non-minimatch program: every hypothesis gets no matching strategy → VERDICT_SKIPPED, no sandbox run, no verdict, no draft. A real run cannot produce a finding.
[CRITICAL] — §1.3(b) "defensible, evidence-backed null" → A real run's null is FORCED by strategy-selection returning SKIPPED (no PoC author), not by evidence the target is clean. That is the exact infra/capability-laundering the workspace forbids, relocated to the strategy layer. A SKIPPED-driven null must NOT count as success.
[CRITICAL] — §3 hb-be9 framing → hb-be9 disambiguates refuted-vs-error inside the templated trigger path, but novel hypotheses never reach derive_verdict (they SKIP first). So hb-be9's trust machinery never engages on the novel path it is meant to protect.
[CRITICAL] — §7 / §2 Stage 1 program selection → No in-scope huntr program is named or confirmed reachable; fetch_program.py needs a concrete --identifier <owner>/<pkg>; "pipeline-chosen from huntr listing" has no implementation (no huntr browse/search API in the codebase). This is a prerequisite, not a deferrable detail — Stage 1 cannot start without it.
```

## IMPORTANT

```
[IMPORTANT] — ordering contradiction → Tracker says "blocked by hb-be9"; §3 says hb-be9 "rides along"; §7 says "recommended: land before Stage-4 checkpoint." Three different orderings. Pick one and state it once.
[IMPORTANT] — §2.1 supervised driver → The six-checkpoint "inspection-halt" mechanism is substantial NEW code, not a deferred decision — BUT it is also over-built: six stage entry points already exist and nightly.py already composes them. Resolve by CUTTING the reusable --supervised/--until flag; a one-time run is manual invocations of existing entry points (or a throwaway sequencing snippet). Add "reusable supervised-run driver" to non-goals, deferred to the nightly-cron-handoff follow-up.
[IMPORTANT] — §3 hb-be9 premise overstated → model.py ALREADY returns VERDICT_ERROR for timed_out=True; the real gap is only non-timed-out infra failures (OOM, uid-1000 denial, import error). Narrow the fix description accordingly.
[IMPORTANT] — §3 existing-test cascade → Tests test_derive_verdict_refuted_sha_mismatch / _exit_mismatch / _both_mismatch assert VERDICT_REFUTED for any non-match — the exact behavior hb-be9 changes. They WILL fail; the plan claims "additive, not a regression repair" and lists no existing-test updates. Enumerate them.
[IMPORTANT] — §3 PocPlan schema change → PocPlan is a frozen dataclass with no optional fields; adding expected_refuted_exit/sha256 as required breaks every constructor site + harness tests simultaneously. Commit to Optional-with-default vs required and state the migration.
[IMPORTANT] — §3 "trigger.js" referent → There is no trigger.js file; it is the _TRIGGER_JS_TEMPLATE string embedded in scripts/verify/templates/*.py. Fix the reference or an executor finds nothing.
[IMPORTANT] — §3 "all exploit templates" → Only ONE template exists, and it is the known-CVE path the novel run won't exercise. The load-bearing change is expected_refuted on the LLM-strategy PocPlan + the derive_verdict ERROR path; the minimatch template update is regression coverage only.
[IMPORTANT] — §2 Stage 3 / §6 LLM provider prerequisite → llm/generate.py select_client() defaults to provider "claude" (needs ANTHROPIC_API_KEY/keyring) else "llama" (needs llama-server at 127.0.0.1:8080). Neither is provisioned or reachability-checked in the plan. LLMUnavailable is caught per-asset and returns [] silently → an unprovisioned LLM yields zero hypotheses that reads as a clean null but is infra failure.
[IMPORTANT] — §1.3(b) null acceptance criterion → No criterion distinguishes a DEFENSIBLE null (hypotheses generated AND genuinely refuted with passing infra) from a STRUCTURAL null (zero hypotheses / all-SKIPPED / LLM-down). They look identical in output. Define the discriminator (e.g., hypotheses_count>0 AND every verdict ∈ {verified, refuted} with infra-clean evidence).
[IMPORTANT] — §4 run journal undefined → It is "the proof artifact" for DoD(b) but has no schema, format, path, required fields, or run-started/run-complete bookend sentinels. An interrupted run's journal is indistinguishable from a complete one. Specify a minimal schema + sentinels.
[IMPORTANT] — §2 Stage 1 huntr shape is PRE-RUN validation → fetchers/huntr.py carries an explicit RECONCILE NOTE that the __NEXT_DATA__ props→pageProps→repo path is inferred/fixture-only; "verify against a real huntr page before production use." Capturing + diffing a real page is a prerequisite step, not an in-run reconcile.
[IMPORTANT] — re-run / idempotency hazards (risk) → harness _persist uses write_text (clobbers runtime/verdicts/<slug>/verdicts.json); ledger append_event has no idempotency guard (double-writes on re-run); _drive_phased reuses workdir without cleaning (stale node_modules can skip the targeted install); mid-loop ScopeViolation discards in-flight verdicts (no finally/persist). A supervised re-run needs a clean-slate or resume story.
[IMPORTANT] — missing evidence-redaction phase → No step between Stage-4 raw sandbox evidence and Stage-6 draft for redacting secrets to evidence/redacted/; the PT-6 secret hook fires on any secret in those writes.
[IMPORTANT] — value: missing do-nothing baseline + named consumer → State the cost of inaction and who consumes the journal / what decision it unlocks (operator sign-off to activate nightly cron? Stage 7 scoping?). Without it the run's value is asserted, not justified.
[IMPORTANT] — value: program representativeness → "proven against real data" from ONE program needs selection invariants (≥N in-scope packages, active bounty, ≥1 advisory so a playbook is selectable, no overlapping open disclosures) or the proof doesn't generalize and isn't falsifiable.
```

## MINOR

```
[MINOR] — §1.3(a) "Tier-1 Citation" → A novel pre-disclosure finding has no NVD/GHSA record; clarify that source code (the fix-diff / vulnerable line) counts as Tier-1 here.
[MINOR] — escalation criterion → No rule distinguishes an in-envelope reconcilable shape gap (continue) from a new blocking gap (halt + escalate). Define it.
[MINOR] — Docker-liveness precheck → sandbox/runner.py shells `wsl -e docker run`; add an explicit "Docker daemon up in WSL2" precheck at Stage-4 entry, else the first verdict is a SandboxError ERROR.
[MINOR] — nightly.py STUBs → stage_refresh_scopes / stage_refresh_disclosed are marked STUB; a supervised driver must route scope-loading through fetch_program.py first. Trace this.
[MINOR] — git clone is unsandboxed (risk) → recon/clone.py runs host-side `git clone` + lockfile parsers on attacker-controlled content, outside the Docker boundary; §5 lists clone as "gated egress" without noting it is unsandboxed.
[MINOR] — non-npm install hooks (risk) → safe_install_env suppresses npm scripts only; pip setup.py / cargo build.rs / gem hooks execute as container root during install. Either restrict v1 to npm targets or note the residual root-in-container risk.
[MINOR] — clone size cap fires late (risk) → recon/clone.py checks size AFTER `git clone --depth 1` completes; up to ~500MB written before rejection. No pre-clone gate.
[MINOR] — OSV/recon degradation (feasibility) → advisories.py treats OSV errors as non-fatal and continues; missing advisories silently weaken Stage-3 signal without a checkpoint failure. Surface as a warning.
[MINOR] — Stages 5/6 "live-proven" caveat → proven via FIXTURE advisories; real recon identifiers (GHSA- prefix mismatches, OSV edge cases, _detail_to_advisory parse failures) are untested against dedup.
```

---

## Bottom line

The spec's organizing claim — *"the machine is wired; the only new build is hb-be9; the run just exercises it on real data"* — does not survive contact with the code. **The pipeline has no PoC-authoring path for novel hypotheses** (`LLMPocStrategy` is an unimplemented stub; the template registry holds one known CVE). Consequences:

- A real-program run produces all-`SKIPPED` verdicts → no draft (criterion *a* unreachable) and a null that is a *capability artifact*, not evidence (criterion *b* is the very anti-slop failure the project forbids).
- hb-be9 — the spec's centerpiece — protects a code path the novel run never reaches.

This is a genuine, correct catch, not a nit. The body of work needs reframing before it can be planned. Three honest paths in the summary message.
