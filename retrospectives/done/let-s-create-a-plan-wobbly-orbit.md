# Retrospective: Adopt the official beads workflow-priming hook (hardened)

**Plan:** `~/.claude/plans/let-s-create-a-plan-wobbly-orbit.md`
**Commit:** `3ba3d6f` (`Add curated PRIME.md override for bd prime workflow priming`, harness-backlog ledger) + `~/.claude` config/hooks (untracked)
**Date:** 2026-06-26 _(transcribed from the in-plan retrospective; executed 2026-06-25)_

## Outcome

Added a curated beads workflow-priming SessionStart hook that re-injects the bd *session-close protocol* (close issues → run gates → check git → conservative handoff) after `/compact` or `/clear`, complementing the existing `inject_backlog.py` live-queue hook. Implemented via a `.cmd`-safe Python shim (`inject_bd_prime.py`) driving `bd prime` against a hand-authored `.beads/PRIME.md` override — chosen over `bd setup claude` verbatim because upstream's baked-in text ("do NOT use MEMORY.md / TodoWrite / track ALL work in bd") collides with this harness's auto-memory + GitHub-issues/beads split. All 5 verification checks pass.

## What worked

- **Routing `bd prime` through a Python shim copied from `inject_backlog.py`** cleanly solved the `.cmd`-shim + silent-fail concerns — `bd` is a Windows `.cmd` the hook runner can't exec directly, and the proven template (inner timeout, `try/except` silent-null, self-built `additionalContext` envelope) needed no rework.
- **Step 0 concurrency stress test** (4× simultaneous `bd ready` + `bd prime`) showed **no Dolt-lock contention** — the embedded-Dolt shared daemon serves concurrent reads — so the planned merge fallback was unnecessary and separate hooks were kept.
- **`bd prime` serves `.beads/PRIME.md` verbatim** (no prepended banner, no BOM), so the `<!-- curated-harness-prime v1 -->` sentinel containment-guard works as designed (the shim suppresses output if the sentinel is absent, defending against an unexpected upstream default).
- **Override-absent guard verified independently** — pointing the shim at a ledger with no PRIME.md emits nothing (exit 0), so a missing override can never leak the conflicting upstream defaults.

## Friction / bugs

- **`git commit` arg order**
  - *What happened:* First commit attempt consumed the message as a pathspec.
  - *Root cause:* `-m <msg>` must precede the `--` pathspec separator.
  - *Fix:* Reordered; committed cleanly.
  - *Rule (generalizable):* In `git commit -m "…" -- <path>`, the `-m` value must come before `--`.

- **Memory-file location ambiguity**
  - *What happened:* The beads-continuity memory could have been edited in the wrong project memory dir.
  - *Root cause:* Two project memory roots exist (`C--Users-Garre` vs `-Workspace`); the continuity file lives under the former.
  - *How caught:* The adversarial review flagged it; resolved via Glob before editing.
  - *Rule:* Verify which project-memory root owns a file (Glob) before editing auto-memory.

- **Dropped redundant ceremony** — the optional Step-4 tracking bead was skipped; the plan, this retro, and the `hb-9yw`-cited memory already record the change. *Rule:* don't add a tracking bead when durable records already exist.

## Concrete improvements

- **`.beads/PRIME.md`** curated override (sentinel + session-close protocol + scoped task-tracking note + `bd --help` pointer) — done, committed `3ba3d6f` to the harness-backlog ledger.
- **`inject_bd_prime.py`** shim (existence-guard + 8s inner timeout + silent-null + sentinel check) — done, live in `~/.claude/hooks/`.
- **`settings.json`** SessionStart registration (after backup + idempotency check + JSON validation) — done; `settings.json.bak` retained as the rollback net.
- **Docs/memory reconciled inline** — `~/CLAUDE.md` SessionStart inventory + the beads-continuity memory updated (no false `hb-9yw.5` supersession claim).
- **Activation:** fires on the next session start (existing sessions don't reload `settings.json`).
