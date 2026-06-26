# Retrospective: Evidence Scope-Binding Hook (D2)

**Plan:** `~/.claude/plans/2026-06-25-evidence-scope-binding-hook.md`
**Commit:** `dfe83a4` (`chore(release): evidence@1.2.0`)
**Date:** 2026-06-25

## Outcome

Shipped `evidence@1.2.0` (PR #10): a ready-made `scope_bind.py` PreToolUse hook that confines `WebFetch` (when the manifest declares `hosts`) and `Edit`/`Write`/`MultiEdit` (when it declares `path_prefixes`) to `.claude/evidence-scope.yaml`, relaying the existing `scope_binding.py` scaffold with a `scope_binding` HMAC override valve. It is **off by default** — registered in the plugin's `hooks.json` but a no-op unless `EVIDENCE_SCOPE_ENFORCE` is on and a manifest is loaded (the `learning`-plugin env-gate idiom). 13 tests, 98% coverage on the hook, all gates green. The delivery form changed twice (global → opt-in → env-gated registration) before landing — both pivots were the right calls, surfaced by review and by implementation reality respectively.

## What worked

- **`/adversarial-review-plan` before execution** — earned its keep again: it challenged the original *enforced-global* premise (no consumer needed it; the README steers framework projects away) and caught a real correctness bug (C2) before a line of code was written.
- **The `learning`-plugin env-gate precedent** — once pure settings.json opt-in proved infeasible, there was a proven, idiomatic answer already in the repo (registered-but-off-via-env). Reusing an established pattern beat inventing one.
- **`release.py --dry-run`** — caught a spurious cross-plugin bump for the *second* time this program (D1: missing tags; D2: orphaned tag). The dry-run is the load-bearing safety check before any release.
- **AskUserQuestion at design forks** — both pivots (global→opt-in, and the opt-in *mechanism*) were genuine user-owned decisions that emerged mid-stream; gating them kept the user in control instead of me guessing.
- **TDD on the env-gate** — wrote the failing "off by default" test first, watched it block (exit 2), then added the gate. The regression for the C2 fix (WebFetch under a path-only manifest) is likewise a first-class test.

## Friction / bugs

- **Opt-in-via-project-settings.json was infeasible**
  - *What happened:* The spec/plan assumed a consuming project would wire the hook into its own `.claude/settings.json`.
  - *Root cause:* `${CLAUDE_PLUGIN_ROOT}` is only defined inside a plugin's *own* hooks; the installed path is version-pinned (`…/cache/.../1.1.0/`); and `scope_bind.py` imports its `scripts/` siblings, so it can't be copied standalone.
  - *How caught:* During Task 2 implementation, by inspecting the install layout and the hook's imports — I stopped execution and asked rather than shipping awkward docs.
  - *Fix:* Env-gated registration in the plugin's own `hooks.json` (the learning idiom).
  - *Rule:* Before designing an "opt-in plugin hook," verify how a *consuming project* references it. `${CLAUDE_PLUGIN_ROOT}` is plugin-hooks-only; the env-gated-registration pattern is the marketplace's proven per-project opt-in.

- **C2: `check_url` rejects-all when the manifest has no `hosts`**
  - *What happened:* The original design would have blocked *every* `WebFetch` under a path-only manifest.
  - *Root cause:* `scope_binding.check_url` returns reject-all on an empty `hosts` allow-list (asymmetric with `check_path`, which is permissive without `path_prefixes`).
  - *How caught:* Adversarial review (feasibility + risk-rollback dimensions, reading the scaffold source).
  - *Fix:* The hook only gates `WebFetch` when `scope.hosts` is non-empty; regression-tested.
  - *Rule:* When a hook relays a scaffold's verdicts, audit the scaffold's *empty-input* returns (empty allow-list ≠ "no restriction") before assuming a permissive default.

- **Squash-merge orphaned the `learning-v1.3.0` tag**
  - *What happened:* `release.py --dry-run` proposed a spurious `learning 1.3.0 → 1.4.0` bump while releasing evidence.
  - *Root cause:* PR #9 (D1) was squash-merged as a new commit on `main`; the pushed `learning-v1.3.0` tag still pointed at the pre-squash branch commit, which is not an ancestor of `main`, so `release.py` saw the squash commit as "unreleased."
  - *How caught:* `release.py --dry-run` (the plan explicitly anticipated a wrong-tag case).
  - *Fix:* Re-pointed `learning-v1.3.0` to the squash commit (`7e60754`) and force-pushed the tag.
  - *Rule:* After squash-merging a release branch, re-point that plugin's release tag to the squash commit on the target branch — squashing orphans the originally-tagged commit.

- **Inline execution left plan checkboxes unticked**
  - *What happened:* `/plan-completion` reported 15 unchecked `- [ ]` tasks though the work was done.
  - *Root cause:* Executing inline, I never edited the plan file to tick boxes as I completed steps.
  - *Fix:* Bulk-ticked them; re-ran → COMPLETE.
  - *Rule:* When executing a plan inline, tick checkboxes as you finish each step (or immediately before `/plan-completion`), so the plan reflects reality.

- **Cross-repo `frontmatter_lint` false-positive (recurring, cosmetic)** — my user-level `discipline` hook requires `diataxis` frontmatter and fires on the marketplace's plain-markdown `docs/` (ADRs, gotchas). Harmless (PostToolUse, edit applies); I do not add foreign frontmatter the repo's own lint doesn't require.

## Concrete improvements

- **Release-tag reconciliation after squash-merge** — this is the *second* tag-hygiene surprise in this program (D1 missing tags, D2 orphaned tag). Worth a small `release.py` guard or a documented "after merging a release PR, reconcile the tag" step. Follow-up.
- **`retrospectives/pending/` still not gitignored** — flagged in the D1 retro too; add it once. Follow-up.
- **Document the env-gated-opt-in idiom** as a reusable marketplace pattern (learning + evidence both use it now) — e.g., a note in `docs/plugin-authoring.md`. Follow-up.
- **Plan-mode + skill re-entry mismatch** — invoking `/adversarial-review-plan` re-entered plan mode tracking the *stale* prior plan file, so D2's `ExitPlanMode` surfaced the wrong plan and no pending marker was dropped for D2. Minor harness friction worth noting for future multi-plan sessions. Done (worked around).
