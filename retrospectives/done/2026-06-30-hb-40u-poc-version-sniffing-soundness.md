# Retrospective: hb-40u — Differential PoC version-sniffing trust assumption + deferred minors

**Plan:** `sec-research/docs/superpowers/plans/2026-06-30-hb-40u-poc-version-sniffing-soundness.md`
**Commits:** `27ad148` (`docs(sec-research): hb-40u document differential-oracle version-sniffing trust assumption`) + `b20ba2e` (`chore(sec-research): hb-40u deferred minors …`)
**Tracker:** closes hb-40u
**Date:** 2026-06-30

## Outcome

R1: an LLM-authored PoC trigger can discriminate the affected from the fixed package by *reading the installed version/metadata* instead of exercising the vulnerability — a perfect-but-meaningless differential that would yield a false `verified`. I drafted a static regex detector to fail such triggers closed; a 3-agent adversarial plan review showed the detector was **net-negative**, and the work pivoted to the bead's other sanctioned option: **document the residual trust assumption**. Shipped: a trust-assumptions note in the verify-harness oracle docstring (recording the assumption *and* why a detector was rejected), a one-line reinforcement of the no-sniff rule in the repair-feedback prompt, and four cheap deferred minors (a symmetric-timeout test, a `build_calls == 1` happy-path assertion, two clarifying comments). Cut with cause: the detector, all `model.py` changes, the `build_plan` ecosystem re-assert, and a redundant terminal ledger event. 417 tests green.

## What worked

- **The adversarial plan review reversed a wrong build before any code shipped.** The detector read like "real security code," but three independent lenses converged on net-negative: the skeptic flagged the **coverage cost** (failing closed on `.version`/`package.json` makes the version-parsing/semver vuln class — an in-scope OSS-supply-chain target — permanently unverifiable) and the **absent live consumer** (no novel auto-discovery yet; the human gate already blocks a false `verified`); the feasibility auditor proved the detector **fails open on trigger naming** (`./trigger.js`, `node -e`, any non-conventional name is never scanned). A guard that simultaneously *misses* real sniffing and *blocks* legitimate targets is worse than none.
- **Pre-verifying the highest-risk interaction myself, in parallel with the agents.** Before the reviews returned I confirmed `_make_diff_plan()` / `_diff_plan()` carry clean trigger sources, so the detector (had it shipped) wouldn't have silently broken every existing differential test. That made the later "cut it" decision cheap and unregretted — I already knew exactly what the detector touched.
- **Honest doc-as-deliverable.** The durable output is the oracle docstring stating the assumption and the rejected-detector rationale — exactly the anti-AI-slop honesty this workspace optimizes for. The analysis (why not to build) was the value, not lines of guard code.
- **Scope-cutter caught a guard for an unreachable state.** The `build_plan` ecosystem re-assert was cut because `supports()` already gates `== npm` and is always called first — validating an impossible scenario, against the standing workspace rule.

## Friction / bugs

- **I almost shipped security theater.**
  - *What happened:* the first plan added a static version-sniffing detector that fails closed to ERROR, framed as "defense in depth."
  - *Root cause:* I reached for a code-level guard because R1 is a real soundness gap, without first weighing the guard's coverage cost, evadability, and whether any consumer is harmed today.
  - *How caught:* the 3-agent adversarial plan review (skeptic + feasibility + scope-cutter), pre-execution.
  - *Fix:* cut the detector; resolve R1 by documenting the residual trust assumption (the bead's sanctioned alternative) + lean on the existing human gate.
  - *Rule:* **before adding a security guard, prove its marginal value over the controls already in place, and price its false-positive/coverage cost.** A bypassable guard that blocks a legitimate case and has no current consumer is net-negative — documenting the residual assumption is the honest move.

- **A blocklist guard against a non-adversarial threat fits the wrong threat model.**
  - *What happened:* the plan justified the detector as defending against *naive* version-sniffing by a capability-limited local model, but a blocklist's weakness is *adversarial evasion* — not the stated threat — while for the naive threat, version-string normalization (no coverage cost) would have been the better-fitting tool.
  - *How caught:* the plan-skeptic.
  - *Rule:* **match the mitigation to the actual threat actor.** For a non-adversarial model, removing the signal at the source beats a blocklist of read-patterns; for an adversary, neither a blocklist nor normalization is a proof — the human gate is.

## Concrete improvements

- **R1 residual-trust documentation** — `verify/harness.py` module docstring records the assumption + the detector-rejection rationale; `poc_prompt.build_poc_prompt` repair addendum reinforces the no-sniff rule. Status: done (27ad148).
- **Deferred minors** — symmetric `fixed.timed_out` test, `build_calls == 1` happy-path assertion, `is_differential` + legacy-single-run-path clarifying comments. Status: done (b20ba2e).
- **Cut with cause (documented in the plan's Out-of-scope):** the static detector; the `build_plan` ecosystem re-assert (unreachable state); the terminal `verify-no-discrimination` event (outcome already non-silent via `verify-verdict`). Version-string normalization and `--read-only` sandbox hardening (hb-nxz) remain available if a future novel-discovery loop makes a false `verified` reachable past the human gate.
- **Carried:** the review lesson — *the highest-value review outcome is sometimes "don't build this," and pricing a guard's coverage cost is part of designing it.*
