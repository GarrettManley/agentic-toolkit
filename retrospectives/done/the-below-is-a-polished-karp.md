# Retrospective: delivery@garrettmanley — generic /deliver lifecycle plugin

**Plan:** `~/.claude/plans/the-below-is-a-polished-karp.md`
**Commit:** `2451331` (`feat(delivery): add /deliver lifecycle plugin`) — in `source/repos/claude-marketplace`
**Date:** 2026-06-29

## Outcome

Turned the user's hand-typed Aether delivery chain (plan → value → docs → review → execute → verify →
review code → land → retrospect) into a reusable, project-agnostic `delivery@garrettmanley` plugin: a
`/deliver` command + skill that runs a fixed lifecycle spine and binds the few project-varying steps
(`plan-writer` / `doc-cluster` / `edit-checklist` / `land-policy`) from a per-repo
`<repo>/.claude/delivery.local.md`. Shipped to `main`, installed, enabled, and confirmed resolving.
The Aether variant was derived locally (gitignored config in the Roleplaying repo), proving the
generic-vs-derived mechanism without committing any project-internal names to the public marketplace.

## What worked

- **`/adversarial-review-plan` before execution** — caught two issues the draft would have shipped: the
  `value-justify` slot was inert (`disable-model-invocation: true`) *and* double-emitting (aether-plan-writer
  already produces the block), and the dev-clone≠live-cache publish gap. Both fixed on paper, zero rework.
- **Parallel Explore agents up front** — three agents mapped marketplace conventions (manifest shape, skill
  vs command idioms, arg/parameterization patterns, the gate set) cheaply before any authoring.
- **"Generic but minimal" trim** — the scope-cutter/skeptic panel pushed config-only binding (no `--flag`
  layer) and 3 slots instead of 9; the smaller surface was faster to build and easier to verify.
- **House-style mimicry** — reading `discipline.local.md`, `pre-plan-brief.md`, `adversarial-review-plan`,
  and `plugin-authoring.md` first meant the new files passed every gate on the first `verify.sh` run.

## Friction / bugs

- **dev-clone ≠ live-cache (the big one)**
  - *What happened:* After all gates passed, `/deliver` "didn't work." My verification step said "sync the
    live cache via `/plugin marketplace update`," implying that would pick up the local dev-clone edits.
  - *Root cause:* The installed `garrettmanley` marketplace is a **git clone of the GitHub repo**;
    `marketplace update` does `git pull` from GitHub, not from the local `source/repos/claude-marketplace`
    working tree. The plugin existed only as uncommitted working-tree changes, invisible to the installed
    marketplace. A feasibility reviewer flagged exactly this (I1); I under-corrected it as "sync" without
    realizing sync = push.
  - *How caught:* User reported it; `git -C <live-cache> remote -v` showed the GitHub origin and 0 delivery
    entries.
  - *Fix:* commit → push to `origin/main` → `marketplace update` → `plugin install` → `reload-plugins`.
  - *Rule:* For a GitHub-backed marketplace, "make a plugin available" = **push to the default branch, then
    install + reload**. Local file edits and even local commits are invisible to the installed marketplace.
    A passing `verify.sh` proves the source is valid, not that the plugin is reachable.
- **Privacy leak in skill examples**
  - *What happened:* SKILL.md's resolved-slot and config examples used real `aether:*` slugs and "Roleplaying".
  - *Root cause:* Reached for the concrete Aether names as the handy illustration in a *generic* artifact.
  - *How caught:* My own `grep -ri aether plugins/delivery/` acceptance check — non-zero hits.
  - *Fix:* Neutral `myproject:*` placeholders; real bindings live only in the local config.
  - *Rule:* Generic/published artifacts use placeholder names; run the privacy grep *before* declaring done.
- **Asserted a file was "committed" when it was gitignored**
  - *What happened:* The Aether `delivery.local.md` body claimed it was trackable "like the committed
    discipline.local.md."
  - *Root cause:* Assumed `.claude/*.local.md` is committed; the Aether repo gitignores all of `.claude/*`,
    so `discipline.local.md` is local-only.
  - *How caught:* `git status` showed no change for the new file; `git check-ignore -v` confirmed.
  - *Fix:* Corrected the body to state it is gitignored/local-only (which also fully resolves the
    accidental-commit risk a reviewer raised).
  - *Rule:* Verify gitignore/tracking state with `git check-ignore` before asserting how a file is tracked.
- **"Installed" ≠ "enabled"**
  - *What happened:* Even after push + `marketplace update`, `/deliver` still didn't resolve until an explicit
    `plugin install delivery@garrettmanley` + reload.
  - *Rule:* Publishing a plugin is three steps the user must run — update, install/enable, reload — none
    implied by the others.

## Concrete improvements

- **delivery@garrettmanley shipped** — `main` @ `2451331`; `/deliver` live, installed, resolving. Done.
- **Roleplaying/.claude/delivery.local.md** — the worked Aether variant (local, gitignored). Done.
- **Document the "make it live" checklist** (push → marketplace update → install → reload) in the plugin
  README or `docs/plugin-authoring.md`, so the dev-clone≠live-cache gap doesn't bite the next plugin. Follow-up.
- **A local-marketplace dev-test path** so `/deliver` (and future plugins) can be exercised before any public
  push — needs resolving the same-`name` collision between the dev clone and the installed marketplace. Idea/follow-up.
