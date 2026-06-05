# Retrospective: Wire Workspace-specific Claude Code capabilities

**Plan:** `~/.claude/plans/let-s-make-sure-this-swift-spindle.md`
**Commit:** `2dee8b4` (`chore(harness): wire Workspace-root Claude Code overlay + verify-commit gate`)
**Date:** 2026-06-04
**Tracker:** hb-8fy (CLOSED)

## Outcome

Closed the deltas a root-launched Claude session does not inherit from `~/`: a thin
`Workspace/CLAUDE.md` overlay (sec-research launch-from-inside footgun, `.ai/` truth-base
pointer, publish-privacy rule), a tracked `.claude/settings.json` wiring a hard-block
`PreToolUse` verify-commit gate (`check_verify_before_commit.py`) with a
`[verify-override:]` valve, a `settings.local.json` tidy (root emptied; sec-research
entries relocated), and `.gitignore` allow-list entries (`!.claude/`, `!CLAUDE.md`,
`!_scripts/`) so the new project config and the mandated scripts are tracked. The
inheritance audit held: the Workspace was ~90% configured via `~/`, so this was delta-
closing, not setup.

## What worked

- **Inheritance audit before building** — established that hooks/context/plugins/agents
  already fire at root, narrowing the job to four genuine deltas and avoiding rework.
- **AskUserQuestion to lock decisions** — overlay-vs-restate, permission relocation, and
  hard-block-with-valve were settled before code, matching the stated hook preference.
- **Reusing the existing hook shape** — `check_verify_before_commit.py` followed the
  `~/.claude` PreToolUse stdin-JSON + `permissionDecision` contract; `pwsh -NoProfile
  -File` via `subprocess.run` worked first try on Windows.
- **Empirical branch coverage** — every gate path was exercised: non-commit→allow,
  override→allow+note, empty-stage→allow, clean→allow, real `TBD`→deny, sec-research-
  only→skip, missing-script→fail-open.

## Friction / bugs

- **`pre_commit_audit.ps1` was slow and fail-closed on an intentional placeholder**
  - *What happened:* the audit ran 20.7s (tripping the gate's 12s timeout → silent
    fail-open) and exited 1 on an intentional `TBD until smoke runs` placeholder in a
    `docs/superpowers/specs/` spec, which would have fail-closed every non-sec-research
    commit.
  - *Root cause:* `Get-ChildItem -Recurse` descended `node_modules`/`site/themes` before
    path-filtering; the placeholder lived outside the existing prune carve-outs.
  - *How caught:* live gate test during execution surfaced both the timeout and the
    false-positive deny.
  - *Fix:* rewrote to a prune-walk (`System.IO.Directory.EnumerateFileSystemEntries` +
    directory-name prune pattern) → 0.6s; extended the prune list with `superpowers`/
    `.superpowers` (same rationale as the pre-existing `archetypes`/`.gemini` carve-outs).
    Per-commit gate now ~1–2s.
  - *Rule:* a verification gate must be fast enough to stay under its own hook timeout,
    and its pass/fail set must exclude intentional placeholders — otherwise it fail-opens
    (useless) or fail-closes (wedges all commits).

## Concrete improvements

- **Verify-commit gate** — `Workspace/.claude/hooks/check_verify_before_commit.py`, tracked
  and live; verified post-commit that both now-tracked `_scripts/*.ps1` resolve at the
  workspace root and exit 0 (no "script not found" fail-open).
- **`_scripts/` tracking (was the lone open follow-up)** — RESOLVED in the same commit:
  `.gitignore:9 !_scripts/` plus the three scripts committed. The plan's "open follow-up"
  note was stale at write time; the durability gap (tracked gate depending on untracked
  scripts) no longer exists.
- **Prune-walk audit** — `_scripts/pre_commit_audit.ps1`, tracked; 20.7s→0.6s.

## Follow-ups (deliberately left to the user)

- **Retrospective tracking policy** — RESOLVED in the follow-up commit: added the
  nested-whitelist idiom (`!retrospectives/`, `retrospectives/*`, `!retrospectives/done/`)
  so `done/` retros accumulate in history while `pending/` markers stay per-machine.
  (The post-commit publish hook is path-gated to `site/`/`.ai/`/`docs/`/`README.md`, so
  tracking retros triggers no Firebase deploy.)
- **HMAC-signed override parity** with sec-research — available upgrade if the lightweight
  `[verify-override:]` valve proves insufficient; not needed so far.
