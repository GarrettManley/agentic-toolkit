# Retrospective: Full Tournament Expansion — Prose Eval Matrix + Gate Hardening

**Plan:** `~/.claude/plans/create-a-plan-for-compressed-quilt.md`
**Commit:** `1572eabc` (`feat(study): broadened prose matrix — 34 fixtures, hardened gates, 31 gold-standard passages`)
**Date:** 2026-06-12

## Outcome

Delivered the full 10-axis × 3-tier prose scenario matrix for spec-045: 34 `ProseCase`
fixtures (31 new + 3 original), 31 gold-standard reference passages, two hardened hard-gates
(`PLAYER_AGENCY_GATE` + `makePovDriftCheck`), and a unified `NO_META_NARRATION` constant.
Phase 1 calibration held on the broadened set — gold-standard ranked #1 with non-overlapping
CI over all three LLMs. Evidence docs updated in `7d17cdd`. Spec-045 retrospective filled in
`ae3e27d` (which also records the subsequent Ollama retirement decision). Updates #172.

## What worked

- **`BASE_CHECKS()` factory pattern** — putting all four shared checks into a single
  parameterised factory (`makePovDriftCheck(pcName?)`) meant that adding a new scenario was
  one fixture declaration; the gates propagated automatically to all 34 cases with no per-fixture
  copy-paste.
- **Adversarial tier as positive controls** — authoring each adversarial passage to *invite*
  the failure mode while a good writer avoids it gave immediately runnable regression tests.
  The negative control sentences confirmed the hardened gates rejected what they previously
  missed without over-rejecting the human passages.
- **`sharedPairs` constraint modelled early** — understanding that new scenarios needed
  matching trial-count coordinates *before* the sweep runs saved a re-sweep. The 1-trial-per-new
  strategy was sufficient; Elo CIs were wider on thin-coverage cells but gold-standard #1 rank
  held with p<0.001 McNemar.
- **Fan-out authoring** — parallel agent authoring per category axis compressed passage
  generation into a single session; the standing Workflow authorization made that automatic.
- **Calibration gate as a stable anchor** — because Phase 1 calibration was already PASS,
  each expansion step could be verified incrementally (add fixtures → add references → sweep →
  confirm gold-standard still #1) rather than needing one big end-to-end run.

## Friction / bugs

- **`NO_META_NARRATION` divergence** 
  - *What happened:* Two fixture blocks had quietly diverged to 3-marker and 6-marker
    implementations of the same check. The refactor to a single constant caught this late —
    only when grepping for all `no-meta-narration` references.
  - *Root cause:* Inline per-fixture check objects (not module-level constants) allow silent
    divergence with no type error to catch it.
  - *How caught:* §2 refactor step explicitly prompted the grep; without it the discrepancy
    would have survived.
  - *Fix:* `NO_META_NARRATION` module constant; `CHECKS` export preserved for
    `extract-failures.ts` backward compat.
  - *Rule:* Any check reused across >2 fixtures must be a named module-level constant, not
    an inlined object literal — drift is invisible at inline scope.

- **`PLAYER_AGENCY_GATE` freeze-frame list: over-rejection risk on "you stand"**
  - *What happened:* "you stand" matched correctly on "you stand resolute" but almost
    rejected a valid combat-positioning line ("you stand in the doorway") — the regex was
    initially too broad.
  - *Root cause:* Phrase anchoring ("you stand X" where X is an emotional/resolve adjective)
    was the right pattern, not bare "you stand".
  - *How caught:* Adversarial positive-control test — the human passage's second-person
    spatial statement tripped an early draft of the gate.
  - *Fix:* Tightened to reject subject+verb+resolve-adjective constructions, not bare
    "you stand/sit/wait".
  - *Rule:* Write a passing human sentence alongside each new gate pattern before finalising;
    positive controls catch over-rejection, not just under-rejection.

- **Ollama runtime retired mid-sweep**
  - *What happened:* The plan specified Ollama (`ollama run`, `run-all.mjs` Ollama lifecycle)
    for model sweeps. Partway through the matrix expansion, Ollama was uninstalled
    (ADR-0012 / issue #173) and the harness was migrated to llama-server (`#174`).
    The plan's §6 sweep instructions became stale before the sweeps completed.
  - *Root cause:* The plan was written when Ollama was the active runtime; the retirement
    decision happened in the same work window.
  - *How caught:* `run-all.mjs` smoke test failed after Ollama was removed.
  - *Fix:* `#174` re-wired `run-all.mjs` to llama-server lifecycle; the `--trials 1`
    coordinate strategy was unchanged. Evidence docs updated to reflect the new runtime.
  - *Rule:* Plans that depend on a specific local runtime should note it as a dependency to
    watch; the beads ledger should link the plan issue and the runtime-retirement issue so
    retirement triggers a plan-scope check.

## Concrete improvements

- **Module-level gate constants are now enforced** — `BASE_CHECKS()` pattern is in place;
  done.
- **Adversarial positive-control discipline documented** — added to the spec-045 methodology
  section; done.
- **Runtime dependency tracking** — flagging `run-all.mjs` Ollama dependency in hb-of7
  scope would have surfaced the conflict earlier; captured in ADR-0012 rationale as a
  process note. Pending: a lightweight "runtime dep" field in the beads ledger schema
  (hb-28u.8 scope, not yet scheduled).
- **1-trial-per-new-scenario Elo stability** — CIs on thin cells were noticeably wider than
  the 5-trial original three. A follow-up Phase 3 sweep at 3 trials on the matrix cells
  would tighten them; tracked as a note in spec-045 §8, not yet scheduled.
