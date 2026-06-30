# Retrospective: hb-0vq Seed-Field Alignment Fix

**Plan:** `sec-research/docs/superpowers/plans/2026-06-30-hb-0vq-seed-field-alignment-fix.md`
**Commit:** `863e5ad` (`feat(sec-research): hb-0vq seed-field alignment — local authoring viable (0.00->1.00 live)`)
**Date:** 2026-06-30

## Outcome

Resolved hb-0vq. A shared recon-aware normalizer (`_normalize_authored`, used by both
`generate_hypotheses` and the eval's `score_track_a`) makes local 7B/4B models score
seed-complete on dependency-cve authoring. Live re-measure: **0.00 → 1.00, 80/80 trials**
across qwen2.5-coder-7b, deepseek-r1-7b, gemma-4-E4B, phi4-mini (gemma3-4b load-skipped).
The fix's founding premise — "version-range reasoning is past local reliability" — was itself
a measurement artifact; the models reason correctly, the gate just didn't credit it. Closed
hb-0vq; filed `hb-26v` for live Track B + the deferred `target.identifier` pin.

## What worked

- **Eval↔production parity as a design constraint.** Putting the normalization in ONE function
  shared by production and the eval (rather than "fix the eval") is what kept the measurement
  honest — and was the difference between fixing the metric and fixing the code.
- **TDD caught a real behavior change immediately.** The `empty_seed` bucket test went red the
  instant recon backfill landed; updating it to the new truth (recon fills identity, so an empty
  model seed is "incomplete," not "empty") documented the change rather than hiding it.
- **The two-stage adversarial review earned its cost twice.** The plan review caught a
  test-fixture bug (rationale < `minLength:40`) *before* execution; the code review caught the
  consequential one below *before* landing.

## Friction / bugs

- **The fix made the eval PASS while making it measure the wrong thing (the important one).**
  - *What happened:* with identity + version recon-supplied, Track-A "complete" collapsed to
    "the model emitted any CVE-shaped string" — `seed_complete` checks `candidate_cve_id` is
    non-empty, not that it corroborates a recon advisory. A hallucinated CVE would score complete.
  - *Root cause:* `seed_complete` never modeled production's full `supports()` gate, which also
    needs `fixed_version` (stamped only on advisory corroboration). My fix amplified the gap by
    making every *other* field free.
  - *How caught:* the silent-failure-hunter code-review agent.
  - *Fix:* `score_track_a` now runs `_resolve_fixed_version` and requires `fixed_version`, so the
    eval models the real gate and rejects uncorroborated CVEs. The 1.00 means the models authored
    the *corroborated* CVE-2022-3517 — provable, not CVE-shaped noise.
  - *Rule:* **when a change makes a metric pass, separately verify it didn't make the metric
    measure something cheaper.** A green eval that rewards the failure mode it exists to catch is
    worse than a red one.

- **Silent trust-boundary mutations needed a trace.**
  - *What happened:* dropping a model-authored install version (when recon lacked one) left an
    accepted-but-un-PoC-able hypothesis with no ledger event, unlike every other boundary in
    `generate_hypotheses`. Package identity could also ride through if recon lacked the field.
  - *Fix:* `hypothesis-version-unresolved` ledger event + drop; package identity is stamp-or-drop.
  - *Rule:* in an evidence-disciplined pipeline, a value-changing boundary decision that discards
    model output must be auditable, not silent.

- **PT-5 hard-blocked the commit on the phrase "npm install" in the message.**
  - *What happened:* the commit message described the install path in prose; the `\bnpm\s+install\b`
    sandbox guard matched the message text and blocked the whole `git add && git commit` command.
  - *Root cause:* the guard scans the submitted command string, including heredoc commit prose.
  - *Fix:* reword to "the package-install command"; recommit.
  - *Rule:* keep registry-install verbs (`npm install`, `pip install`, …) and `Stop-Process` out
    of submitted command strings in this workspace — these guards over-match prose. Also: a
    PreToolUse block kills the *entire* compound command, so the `git add` never ran — re-stage
    before retrying, don't assume the index is set.

## Concrete improvements

- **`hb-26v`** — live Track B (end-to-end PoC viability; seed-complete ≠ working PoC) + pin
  `target.identifier`/`asset_type`/`ecosystem` from recon (close the latent seed-vs-target
  divergence via a divergence-drop, not a naive pin that moots the scope gate). Status: open (P3).
- **Eval now models `supports()` end-to-end** — Track-A is an honest proxy for production
  PoC-readiness, including CVE corroboration. Status: done (this commit).
- **Optional follow-ups noted in `hb-26v`:** `score_track_a` `incomplete` bucket; prompt-hardening
  so models emit canonical keys + the resolved version directly.
