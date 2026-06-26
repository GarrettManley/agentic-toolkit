# Retrospective: Learning Plugin — Nightly Deterministic Instinct Synthesis (close the headless loop)

**Plan:** `~/.claude/plans/let-s-write-a-plan-quizzical-garden.md`
**Commit:** `31396e7` (`feat: close the headless self-improving instinct loop (learning + stewardship) (#20)`)
**Date:** 2026-06-26

## Outcome

Shipped a headless self-improving loop across two marketplace plugins: `learning` (→1.5.0) gained `synthesize_nightly.py`, which runs the existing deterministic Phase 2b frequency synthesis across *every* observed project unattended; `stewardship` (→1.4.0) gained a "Learned Instincts" morning-briefing section that consumes the run's data-root report. No LLM, no live session, no manual step. PR #20 squash-merged to `main`; both plugins released via `ci/release.py` and tagged (`learning-v1.5.0`, `stewardship-v1.4.0`). The notable shape of this plan: it started as a 5-phase *LLM*-driven headless miner and was descoped — before any code — to a ~3-phase deterministic automation after adversarial review found the premise was wrong.

## What worked

- **Adversarial plan review before coding** (`/docs:adversarial-review-plan`) — the `plan-skeptic` archetype read the actual source and discovered Phase 2b is already deterministic + headless, collapsing a 5-phase LLM build into a 3-phase one. The single highest-leverage event of the whole task, and it cost only a parallel agent dispatch.
- **AskUserQuestion at every real fork** (direction → write-policy → premise-resolution → merge-path) kept the user steering decisions that were genuinely theirs, instead of me guessing.
- **TDD red-green discipline** — every new function had a failing test first; the headless-scope correctness (iterate `projects/*/` instead of cwd) was provable, not asserted.
- **"One seam" reuse** — `synthesize`, `write_instincts`, `build_observation_summary` were reused verbatim; the new code was a thin iterator + report writer. Small surface = small risk.
- **Validating generated artifacts, not just source** — parse-checking the PowerShell wrapper that `register_nightly.ps1` *emits* (with `-LearningScript` set) caught nothing this time but is the right altitude for code-that-writes-code.
- **CI-faithful local gates before commit** — running the combined coverage exactly as CI does (98% vs ≥90% floor) plus a real cross-plugin E2E meant zero CI surprises across two pushes.

## Friction / bugs

- **v1 plan rested on a false premise (LLM "required" for headless mining)**
  - *What happened:* The first plan assumed all existing instinct paths need a live session and designed a 5-phase local-LLM miner.
  - *Root cause:* I mirrored the Phase 2d retro-mining *shape* so faithfully that I inherited its assumption (a model authors candidates), without checking that frequency synthesis (2b) already creates instincts deterministically with no model.
  - *How caught:* `plan-skeptic` agent in `/docs:adversarial-review-plan`, which read `synthesize.py` + the plugin README and cited the contradiction.
  - *Fix:* Descoped to nightly-2b; deferred the LLM tier to a future bead gated on a spike proving it beats the deterministic baseline.
  - *Rule:* When extending a system by mirroring an existing flow, explicitly separate that flow's *essential* assumptions from its *incidental* ones before inheriting them.

- **Scheduled job would have mined nothing (cwd/project-context trap)**
  - *What happened:* A naive runner would call `get_project_id()` inside the 03:00 task.
  - *Root cause:* `get_project_id()` hashes the scheduler's cwd, which has no `observations.jsonl` — so it resolves a project with zero data.
  - *How caught:* `plan-feasibility-auditor` + dimension agents flagged it; confirmed against `storage.py`.
  - *Fix:* `iter_project_dirs()` globs `projects/*/` explicitly; the runner never calls `get_project_id()`.
  - *Rule:* Headless/scheduled entrypoints have no cwd identity — never derive project/user context from cwd in a scheduled job; iterate the data store directly.

- **Claimed a "safety net" without reading its threshold**
  - *What happened:* The draft plan asserted the SessionStart surface threshold would brake auto-written ≤0.80 instincts.
  - *Root cause:* `surface.py` `DEFAULT_MIN_CONFIDENCE = 0.6`, *below* the 0.80 cap — so candidates would surface immediately; the "net" didn't exist as described.
  - *How caught:* feasibility auditor read the actual constant.
  - *Fix:* For the chosen 2b-only path it's moot (these are the same `auto-frequency` instincts manual `--write` already produces; automation changes cadence, not posture) — documented rather than over-engineered.
  - *Rule:* Don't assert a safety mechanism in a plan without reading the concrete constant/threshold that implements it.

- **Release-vs-squash ordering (initially gave wrong guidance)**
  - *What happened:* I first told the user the release bump (`release.py --apply`) happens *post-merge*.
  - *Root cause:* `release.py` derives per-plugin version bumps from commit *scopes* (`feat(learning)` / `feat(stewardship)`), which a squash-merge collapses into one subject — so a post-merge run would see no scoped commits and skip the release.
  - *How caught:* Re-read `docs/adr/0012-tag-after-merge.md` before merging, prompted by noticing the multi-plugin scope-collapse risk in a squash.
  - *Fix:* Correct order — `--apply` on the branch (pre-squash) to bake in the bump, push, squash-merge, then `--tag` on `main`.
  - *Rule:* With scope-driven release automation + squash merges, the version bump must run on the branch *before* the squash; tags are born on `main` after.

## Concrete improvements

- **`synthesize_nightly.py` + `synthesize-nightly` CLI** (learning 1.5.0) — done, shipped.
- **Learned Instincts briefing section + `register_nightly.ps1 -LearningScript`** (stewardship 1.4.0) — done, shipped.
- **Deferred LLM-tier mining** (non-frequency signal: error clusters, cross-tool semantics) — follow-up; bead not yet filed.
- **Machine activation** — pending, user-gated: `register_nightly.ps1 -LearningScript <learning-install>/scripts/synthesize_nightly.py`.
- **Agent-quality note:** the `Explore` agents (scoping) and the `docs:plan-*` archetypes (review) produced clean, high-signal output; the premise catch in particular justified the whole adversarial-review step. No agent produced misleading output this run.
