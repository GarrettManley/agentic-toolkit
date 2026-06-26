# Retrospective: Activate the `learning` plugin + build Phase 2 (auto-learn from observations)

**Plan:** `~/.claude/plans/fuzzy-imagining-ladybug.md`
**Commit:** `8fe8d9f` (`feat(learning): Phase 2b auto-create instincts + surfacing hook (1.2.0)`)
**Date:** 2026-06-26 _(retro written retroactively; the work shipped 2026-06-25)_

> Written after the fact to clear a missed pending marker. The execution-time friction was not captured live, so this retro reports verifiable outcomes from the plan + shipped artifacts and is explicit about what wasn't recorded, rather than inventing detail.

## Outcome

Took the `learning` plugin from Phase-1-only and dormant to a working auto-learning loop, shipped as **learning v1.2.0**: (A) activated the observation hooks via the two env-var gates so tool-use accumulates to `observations.jsonl`; (B) built Phase 2b — `synthesize.py` converts frequency patterns (tool-pair sequences → `workflow` instincts, bash prefixes → `tooling` instincts) into `auto-frequency` instincts via a saturating, capped confidence model, with a `synthesize` CLI + `/instinct-synthesize` command; (C) added the opt-in `surface.py` SessionStart hook so stored instincts actually inject into context. This is the foundation the later nightly-automation work (`let-s-write-a-plan-quizzical-garden`, learning 1.5.0) built directly on top of.

## What worked

- **Reusing the existing `analyze.py` detectors** — Phase 2b was a thin synthesis layer over already-shipped pattern detectors, not new analysis.
- **Saturating, capped confidence model** (`min(MAX_CONF, consistency·n/(n+K))`) — reserves the top band for human/validated instincts and is monotonic, so auto-instincts are visibly distinguishable from promoted ones.
- **Deterministic ids + parse-before-clobber writer** — `auto-seq-…`/`auto-bash-…` ids make re-runs reinforce rather than duplicate, and the writer never overwrites a non-`auto-` (human-promoted) file. This idempotency is what made the later nightly automation safe to run unattended.
- **Gated, opt-in surfacing** — the SessionStart injection is double-gated (`LEARNING_SURFACE` + strict profile) and confidence-filtered + capped, bounding its context cost.

## Friction / bugs

- **Not captured at execution time.** The pending retro marker was missed, so per-bug root-cause/how-caught detail from the original session is unavailable. Known open thread carried forward into the 1.5.0 work: the surfacing threshold (`DEFAULT_MIN_CONFIDENCE = 0.6`) sits *below* the auto-instinct cap (0.85/0.70), so auto-instincts surface immediately — flagged later in `let-s-write-a-plan-quizzical-garden`'s adversarial review as a "safety net" that isn't one. Rule recorded there.
- **Observation privacy caveat (design-time, accepted):** with observation global, `tool_input` is recorded verbatim for every project; the plan deferred a sanitize-and-exclude guardrail and relied on per-corporate-repo `LEARNING_OBSERVE=off`. Still an open guardrail to revisit if it bites.

## Concrete improvements

- **`synthesize.py` + `synthesize` CLI + `/instinct-synthesize`** (learning 1.2.0) — done, shipped.
- **`surface.py` SessionStart hook** + `LEARNING_SURFACE*` env vars — done, shipped.
- **Observation activation** (settings.json env gates) — done.
- **Follow-on:** nightly headless automation of this synthesis — done later as learning 1.5.0 (`let-s-write-a-plan-quizzical-garden`).
- **Deferred guardrail:** sanitize/exclude for verbatim `tool_input` capture — still open.
