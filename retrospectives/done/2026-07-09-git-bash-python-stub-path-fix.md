# Retrospective: Fix bare `python` resolving to the WindowsApps PyManager stub

**Plan:** `~/.claude/plans/our-next-highest-value-majestic-trinket.md` (reused slug — second body of
work under it; see `retrospectives/done/our-next-highest-value-majestic-trinket.md` for the first)
**Tracker:** `hb-7si`
**Date:** 2026-07-09

## Outcome

Fixed the environment gotcha flagged as a follow-up in the prior `hb-0nh` retrospective: bare `python`
in Git Bash resolved to the WindowsApps PyManager app-execution-alias dispatcher, which hangs
non-interactively instead of erroring cleanly. Applied two machine-config changes (no code commit):
an idempotent PATH prepend of the real interpreter in `~/.profile`, and removal of the two
WindowsApps `python.exe`/`python3.exe` alias symlinks (keeping `py.exe`/`pymanager.exe` intact). Both
verified with live positive evidence across Git Bash, cmd, and PowerShell, and confirmed fixed
*within this session* — no restart needed, since the Bash tool's login shell re-sources `~/.profile`
per call.

## What worked

- **Root-causing from live machine state, not the prior retrospective's framing.** The retro said
  "worth a PATH-level fix" without specifying where. Actually inspecting effective PATH order (with
  indices) surfaced a fact that changed the design: the winning `WindowsApps` entry comes from
  **Machine** PATH, not User PATH — so the "obvious" fix (reorder User PATH) would have silently failed
  (Machine PATH still wins, and editing it needs admin). Caught before ever proposing it.
  Generalizes the "read the actual source" rule from the *previous* retro to environment/PATH state,
  not just code.
- **Validating the fix mechanism read-only before touching anything.** `PATH="<real>:$PATH" bash -c
  '...'` proved the resolution outcome (real interpreter, exit 0) with zero persisted changes, before
  the plan was even written. Cheap and conclusive — turned "I think this will work" into "this works."
- **Discovering the Bash tool's login-shell/`.profile` behavior empirically.** Checked `shopt
  login_shell`, confirmed `.bash_profile`/`.bash_login` are absent (so `.profile` is the real target,
  not `.bashrc`), and proved it experimentally by reading already-exported vars
  (`LEARNING_OBSERVE`/`LEARNING_HOOK_PROFILE`) rather than assuming shell semantics from memory. This
  is what made the "fixes this session, no restart" claim true rather than aspirational.
- **AskUserQuestion for the one real scope fork.** Git-Bash-only vs. also-disable-Store-aliases was a
  genuine risk/coverage trade-off (deletion + regeneration-on-update risk vs. broader coverage) — surfaced
  with concrete previews rather than picking silently. User chose the broader option.
- **Reproducing the failure live before and the fix live after**, in the same session, with the same
  user-visible symptom (`timeout 8 python --version` → exit 124 before; `python --version` → 3.14.3,
  exit 0 after) — the clearest possible before/after evidence.

## Friction / bugs

- **Plan-file slug collision with a prior *retrospective*, not the plan.** The plan-mode slug
  (`majestic-trinket`) was reused from the previous session's already-completed, already-retro'd body
  of work. Overwriting the plan file was correct (system-reinstructed as a fresh planning session), but
  blindly reusing the same slug for *this* retro would have clobbered the hb-0nh retro record.
  - *Root cause:* the retro skill's default output path is keyed off the plan slug, and plan-mode
    slugs aren't unique across distinct bodies of work when a prior plan file gets reused/overwritten.
  - *How caught:* checked `retrospectives/done/` for the slug before writing, per a previously-learned
    instinct ("write the new plan to a fresh dated path... drive `/plan-completion` +
    `/plan-retrospective` by explicit path").
  - *Fix:* wrote this retro under a fresh dated slug (`2026-07-09-git-bash-python-stub-path-fix.md`)
    instead of the reused plan slug.
  - *Rule:* when a plan-mode slug is reused across sessions for unrelated work, the retro's output path
    must be derived independently (dated slug), never assumed identical to the plan-file slug.
- **The pre-existing `pre_commit_audit.ps1` TBD failures reproduced exactly as flagged last session**
  (same 16 errors, same files) — confirms they're stable/pre-existing, not session noise, and still
  unrelated to any work done in either session. Still not filed as a tracked item (see below).

## Concrete improvements

- **`hb-7si`** — filed and closed this session (Workspace machine-config fix; no code commit
  associated — the fix lives in `~/.profile`, outside any repo).
- **`hb-0nh`'s deferred follow-up is now resolved.** The retrospective chain (`hb-0nh` → this) is
  closed end-to-end.
- **16 pre-existing `pre_commit_audit.ps1` TBD failures** — reproduced a second time, still not filed.
  Worth filing now that it's been observed stable across two sessions rather than assumed transient.
- **PyManager alias regeneration risk** — noted in the plan as a known limitation (a PyManager update
  could recreate the WindowsApps `python.exe`/`python3.exe` aliases); the `~/.profile` prepend is the
  durable backstop regardless. No bead filed — revisit only if it actually regresses.
