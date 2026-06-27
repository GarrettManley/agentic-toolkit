# Retrospective: Prove the sec-research verify/sandbox layer live (Docker activation)

**Plan:** `~/.claude/plans/writing-plans-let-s-write-a-curious-sparkle.md`
**Commit:** `73644f4` (`feat(sec-research): activate + live-prove Stage-4 sandbox/verify harness`)
**Date:** 2026-06-26

## Outcome

Installed Docker Engine 29.6.1 in the Ubuntu/noble WSL2 distro and ran the sec-research
Stage-4a sandbox + Stage-4c verify harness against real containers for the first time
(`VERIFY_LIVE=1 pytest` → 348 passed / 1 skipped). The live run did exactly what it was
scoped to do: it surfaced a real exploit-correctness bug that 294 offline tests had never
caught, plus a latent false-negative design hole in the verdict logic. Hardened the sandbox
execute phase to non-root, corrected the minimatch CVE-2022-3517 probe, and brought the
CHARTER / docstrings / orientation doc back in sync with the now-wired pipeline. Net: the
sandbox+verify harness is **proven live**; autonomous novel-finding discovery remains the
next epic.

## What worked

- **The plan's rescope (adversarial-review-plan before execution).** The original "drive to a
  first real submittable finding" goal was unreachable by design (triage dedups known CVEs);
  five review agents caught it pre-execution. Rescoping to "prove the harness live" was the
  difference between a plan that could finish and one that couldn't.
- **"Unhardened-first" ordering.** Proving function (Phase 2) before adding `--user` hardening
  (Phase 3) isolated the exploit-template bug from any hardening-induced breakage — when a test
  failed, the cause was unambiguous.
- **Probing root cause against ground truth, not assumptions.** Extracting both minimatch
  versions' `minimatch.js` and diffing them turned a guessed fix into a verified one.
- **systemd already on in WSL2.** Collapsed the plan's single CRITICAL risk (wsl.conf edits /
  Postgres-killing restart) to nothing — Docker auto-starts reboot-persistent and the docker
  group was picked up without any distro restart, so the Postgres co-tenant was never touched.
- **Adversarial code review at close-out.** silent-failure-hunter found the verdict-laundering
  hole that neither the implementer nor the live tests would have surfaced (the happy path is
  immune).

## Friction / bugs

- **minimatch probe tested the wrong guard**
  - *What happened:* The CVE-2022-3517 template fed a 70000-char pattern to
    `minimatch(path, OVERLONG)` expecting 3.0.4 to pass silently and 3.0.5 to throw. Both
    threw "pattern is too long"; both scored `refuted`.
  - *Root cause:* minimatch's `parse()` has had a 64KB length guard since long before the CVE.
    The probe hit that pre-existing guard (present in both versions), not the guard the fix
    added. The 3.0.5 fix actually added `assertValidPattern` to `braceExpand()` specifically.
  - *How caught:* First-ever real container run (`VERIFY_LIVE=1`). The injected-runner unit
    tests had returned the *expected* hash, so they proved the harness plumbing, never the
    exploit premise.
  - *Fix:* Probe `minimatch.braceExpand(OVERLONG)` directly — unguarded in 3.0.4, guarded in
    3.0.5. Verified against the 3.0.4-vs-3.0.5 source diff; 3.0.4 → verified, 3.0.5 → refuted.
  - *Rule:* A verification template's version-split assumption is unproven until it runs against
    real artifacts of *both* the affected and fixed versions. An injected runner that returns
    the expected output tests the harness, not the claim.

- **Verify harness launders infra-failures into `refuted`** (deferred — hb-be9, P1)
  - *What happened:* `derive_verdict` maps any non-(exit0 + VULN_CONFIRMED-hash) trigger result
    to `REFUTED`. An infra failure (uid-1000 can't read `/work`, missing module, OOM) is
    silently scored "patched."
  - *Root cause:* No "refuted signature" exists — the template declares only the verified
    signature, so the harness can't distinguish a real refutation from an error. The trigger.js
    `catch` is correspondingly too broad.
  - *How caught:* `/adversarial-review-code` silent-failure-hunter, tracing the trigger exit →
    verdict path. The happy path (minimatch 3.0.4 → verified) is immune, so tests wouldn't show it.
  - *Fix:* Deferred to **hb-be9** — needs a refuted-signature in PocPlan, a `VERDICT_ERROR` path
    in `derive_verdict`, a trigger-phase infra guard, narrowed catch, and tests. A trigger.js-only
    half-fix was rejected as misleading (derive_verdict would still launder).
  - *Rule:* A "verified-only" pipeline must treat *unrecognized* outcomes as errors, never as the
    negative verdict — silently mapping "didn't confirm" to "not vulnerable" manufactures
    false-negatives, the exact failure such a workspace exists to prevent.

- **Stale "skeleton/stub" docs across the repo**
  - *What happened:* `nightly.py` docstring + `stage_briefing` strings + `CHARTER.md` roadmap +
    `sec-research/CLAUDE.md` all claimed Stages 3-4 unimplemented, contradicting the wired code.
  - *Root cause:* Docs weren't updated as Stages 2/3/4 shipped across prior cycles.
  - *How caught:* adversarial-review-plan (completeness) flagged it; code-reviewer re-flagged the
    briefing-vs-docstring contradiction after a partial fix.
  - *Fix:* Updated all four to reflect wired/live reality; CHARTER roadmap statuses reconciled
    against closed beads.
  - *Rule:* When a stage ships, update the orientation docs in the same PR — a "SKELETON" docstring
    on wired code actively misleads the next session.

## Concrete improvements

- **Docker-in-WSL2 install runbook** — `sec-research/docs/superpowers/runbooks/2026-06-26-docker-wsl2-install.md`; done (closes 4a spec §8 gap).
- **minimatch template fix** — `scripts/verify/templates/npm__minimatch__CVE_2022_3517.py`; done.
- **Sandbox execute-phase non-root** — `scripts/sandbox/runner.py` (`EXEC_USER`); done.
- **Verdict-laundering disambiguation** — hb-be9 (P1); follow-up (own Stage-4c cycle + tests).
- **Doc-sync** — `nightly.py`, `CHARTER.md`, `sec-research/CLAUDE.md`; done.
- **Hardening backlog** — pip/cargo/rubygems install-script neutralization, egress proxy, phased `--network none` split; tracked on hb-nxz.
