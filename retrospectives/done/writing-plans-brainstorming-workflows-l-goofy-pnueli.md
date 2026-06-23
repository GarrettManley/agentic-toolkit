# Retrospective: sec-research Stage 4c — Sandboxed Verification Harness

**Plan:** `~/.claude/plans/writing-plans-brainstorming-workflows-l-goofy-pnueli.md`
**Commit:** `0f8ac2f` (`docs(stage4c): correct live-test docstring to guard-presence mechanism`)
**Date:** 2026-06-23

> _Reconstructed post-hoc from the git commit trail (`d044ca8..0f8ac2f`, 11 commits) and handoff memory — the executing session did not author this retro. Findings below are commit-evidenced, not first-hand execution capture._

## Outcome

Shipped the reasoning→evidence bridge: `nightly.stage_verify` now turns each Stage-4b hypothesis into a per-hypothesis PoC, runs it through the Stage-4a sandbox with a phased install→trigger split, and emits `verified`/`refuted`/`skipped`/`error` verdicts backed by deterministic evidence (`exit_code` + `stdout_sha256`), persisted to `runtime/verdicts/<slug>/`. A `PocStrategy` Protocol ships a deterministic `templated` strategy (minimatch CVE-2022-3517 vertical slice) with an `LLMPocStrategy` seam defined-but-not-wired. This is the gate that stopped this plan's successor (Stage 5/6) from drafting un-reproduced hypotheses.

## What worked

- **Strategy Protocol + closed LLM seam** — the `TemplatedPocStrategy` (ships) / `LLMPocStrategy` (`supports()→False`) split proved durable: Stage 6's `FINDING_TEMPLATE_REGISTRY` + `LLMFindingTemplate` directly mirrored this shape a session later. A good seam pattern compounds.
- **Two-phase install→trigger with a shared bind-mounted workdir** — cleanly separated the only networked phase (install, host-gated) from an airgapped `--network none` trigger, reusing `sandbox_run` as-is with no Stage-4a extension.
- **Pure reuse of Stage 4a** — the plan's "reuse, do not reinvent; cite the seam paths" discipline meant 4c added zero changes to the sandbox layer.

## Friction / bugs

- **The vertical-slice determinism mechanism pivoted mid-implementation**
  - *What happened:* The plan specified a constant-sentinel approach — a ReDoS watchdog/deadline emitting a fixed sentinel line + exit code, with variable timing kept out of stdout. The shipped implementation (`acecae6`) instead uses a **guard-presence probe** (detecting whether the fixed-version's guard code path is present) plus a versioned `target_identifier` and a `package.json` stub.
  - *Root cause:* A timing-watchdog sentinel is harder to make bit-for-bit deterministic across container runs than predicted; presence/absence of the fixed-version guard is a cleaner, genuinely deterministic signal for the `3.0.4`→`verified` / `3.0.5`→`refuted` boundary.
  - *How caught:* During template authoring / live-test bring-up (the plan's own anti-fabrication gate forced confirming the real mechanism against the package).
  - *Fix:* Shipped guard-presence as the actual mechanism.
  - *Rule:* A vertical-slice "determinism mechanism" is a hypothesis until proven against the real artifact — treat the plan's mechanism as provisional and confirm reproducibility empirically before pinning expected hashes. (Stage 5/6 inherited this benefit: the minimatch case is a *true-negative* there, consistent with the guard-presence reality.)

- **Documentation/comment drift trailing the pivot**
  - *What happened:* After the mechanism pivot, the live-test docstring and an inline comment still described the original sentinel/timing approach (`23176b8` "fix stale comment", `0f8ac2f` "correct live-test docstring to guard-presence mechanism").
  - *Root cause:* Comments/docstrings written against the planned mechanism weren't swept when the mechanism changed.
  - *How caught:* Follow-up doc commits after the implementation landed.
  - *Rule:* When a mechanism pivots mid-build, immediately grep the comments, docstrings, and test names that described the original — they are silent drift the tests won't catch.

- **Stale `select_strategy` test surfaced by the seam commit** (`f3a01b7`) — landing the `LLMPocStrategy` seam required fixing a pre-existing `select_strategy` test. Minor; a reminder that adding a dispatch branch can invalidate dispatch tests.

## Concrete improvements

- **Seam pattern validated and reused** — the Protocol + closed-stub seam is now a standing pattern across verify (4c) and draft (Stage 6).
- **Empirical determinism check before hash-pinning** — fold "prove the mechanism is deterministic against the real artifact before pinning `expected_*_sha256`" into any future exploit-template task brief.
- **Docker-gated live coverage remains opt-in** — `VERIFY_LIVE=1` test exists but the WSL2/docker run is still the gating dependency (shared with `hb-ctr`); same caveat carried into Stage 5/6.
