# Retrospective: sec-research Stage 4b — LLM Hypothesis Generation

**Plan:** `~/.claude/plans/writing-plans-expressive-puddle.md`
**Commit:** `3d956a4` (`fix(stage4b): cover hypothesis drop-paths + doctor ScopeViolation catch + evidence_seed contract doc`)
**Date:** 2026-06-23

> _Reconstructed post-hoc from the git commit trail (`ec5e3cb..3d956a4`, 8 commits) and handoff memory — the executing session did not author this retro. Findings below are commit-evidenced, not first-hand execution capture._

## Outcome

Filled the `stage_hypothesize` stub: an LLM now reads each Stage-3 recon item plus relevant class playbooks and emits scope-bounded, schema-validated candidate vulnerability hypotheses that feed Stage 4c. Built the workspace's first LLM client — provider-agnostic (`LLMClient` Protocol) with two stdlib-only adapters (Claude Messages API default, local llama-server opt-in) behind one `complete_json`, all egress routed through `policy.check_http` before the socket opens. Added `schema/hypothesis.schema.json`, a markdown playbook loader, an injection-fenced deterministic prompt builder, and an orchestrator that stamps server fields, validates, hard-drops out-of-scope targets, and persists to `runtime/hypotheses/<slug>/`. Merged at 190 passing / 2 skipped.

## What worked

- **Clean 8-task linear decomposition** — schema → egress chokepoint → client+adapters → playbook loader → prompt builder → orchestrator → wire+doctor+live → review-fix. The commit trail maps 1:1 to the plan's tasks with no reordering, a sign the plan's file/interface boundaries were right.
- **Egress chokepoint mirroring `recon/_http.py`** — `post_json` gates via `check_http` before the socket and supports `from_fixture=` for socket-free tests; the default suite makes zero network calls. This "gate-then-open, fixture-seam" pattern was reused again in Stage 4c and the broader pipeline.
- **Provider-agnostic from day one** — two adapters behind one Protocol means local-vs-cloud hypothesis quality can be A/B'd later without a rewrite, at near-zero extra cost because both are thin `build_payload`/`parse_response` pairs.
- **Cold-start guard** — zero playbooks loaded ⇒ `generate_hypotheses` returns `[]` without calling any LLM. Structurally forecloses the open-ended "find vulns" hallucination path the workspace exists to avoid.
- **`keyring` + env-fallback key resolution, never logged/persisted/prompted** — secret discipline built into the adapter, not bolted on.

## Friction / bugs

- **Negative/drop paths under-covered until the final review**
  - *What happened:* The final multi-dimension review (memory: "3-dim review found gaps") produced `3d956a4`, which had to (1) add coverage for the **hypothesis drop-paths** (out-of-scope targets that are hard-rejected with a ledger note), (2) fix the **doctor's `ScopeViolation` catch**, and (3) document the **`evidence_seed` contract** (which fields Stage 4b seeds vs. which Stage 4c fills).
  - *Root cause:* The scope-rejection drop path and the doctor reachability path were implemented happy-path-first; the "what happens when the model targets an out-of-scope asset / when the provider is unreachable" branches lacked explicit tests, and the inter-stage `evidence_seed` handoff was implicit.
  - *How caught:* Final whole-feature review, not the per-task gates — the drop/error branches don't fail any happy-path test.
  - *Fix:* `3d956a4` added the negative-path tests, the doctor catch, and the contract doc.
  - *Rule:* Scope-rejection / drop paths and doctor/health-check error paths are the highest-risk under-tested surfaces in a gated pipeline — brief them as explicit negative-test requirements per task, don't leave them for the final sweep. (Stage 5 applied this: triage's "non-verified verdicts dropped" and "no-CVE always novel" paths were unit-tested from the first task.)

- **Inter-stage contract was implicit until documented** — the `evidence_seed` handoff (4b seeds `package_ecosystem`/`package_name`/`affected_versions_range`/`candidate_cve_id`; 4c fills `vulnerable_function_path`) wasn't written down until the fix commit. An undocumented contract between two stages is a latent drift source.
  - *Rule:* When stage N produces a partially-filled structure that stage N+1 completes, document the field-ownership split at the boundary as part of the producing task, not retroactively.

## Concrete improvements

- **Negative-path-first briefing** — drop/reject/unreachable branches became explicit per-task test requirements in the successor (Stage 5/6) plan; carry this forward to every gated-pipeline stage.
- **Reused patterns** — the policy-gated `post_json` chokepoint and the provider-agnostic Protocol+factory seam are now standing patterns; the `from_fixture=`/injected-client offline-test seam keeps the suite network-free.
- **Document inter-stage contracts at the producer** — the `evidence_seed` ownership split is the model; make field-ownership docs a deliverable of the producing task.
