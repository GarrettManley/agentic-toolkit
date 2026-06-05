# CLAUDE.md — Workspace overlay

Thin Claude-Code overlay for `C:\Users\Garre\Workspace`. Portable project knowledge
(roots, environment, git, hardware, working preferences) is already in context via
the parent `~/CLAUDE.md` → `~/AGENTS.md`, whose **Workspace** section governs here
(corporate-repo isolation, surgical-edit preference, the `_scripts/` verify
discipline). This file adds **only** the Workspace-internal specifics that the
portable layer doesn't carry.

> `GEMINI.md` is the Gemini-CLI binding contract and is written in Gemini's tool
> vocabulary (`replace`/`write_file`/`grep_search`). Claude Code does not auto-load
> it; the equivalents here are `Edit`/`Write`/`Grep`. The substantive rules already
> reach you via `~/AGENTS.md`.

## sec-research/ — hooks only fire when launched from inside it

`sec-research/` enforces **17 hard-block rules** (scope-bounding, evidence
discipline, secret-scan, submission gate) via `sec-research/.claude/settings.json`,
whose hook paths resolve through `${CLAUDE_PROJECT_DIR}`. That variable only points
at `sec-research/` when **Claude is launched from inside that directory**.

**Opening Claude at the Workspace root and editing files under `sec-research/` runs
NONE of those hooks — silently.** For any recon / evidence / findings work, start a
session with `claude` from inside `sec-research/`, and read `sec-research/CLAUDE.md`
(the canonical orientation doc + hook map). Don't do `sec-research/` work from a
root-launched session.

## On-demand context (`.ai/` truth-base)

The Workspace keeps a verified truth-base under `.ai/`. These are **not**
auto-injected (to stay high-signal) — read them when doing substantive work in their
area:

- `.ai/context/workspace-architecture.md` — layout, project roots, the hybrid model.
- `.ai/context/conventions.md` — repo-wide conventions.
- `.ai/context/agent-permissions.md` — what local agents may touch.
- `.ai/context/python-standards.md` — Python style for this repo.
- `.ai/adr/` — architectural decision records (001 foundation, 002 local
  orchestration, 003 local script autonomy).

(Skip `hardware-profile.md` / `user-persona.md` / `memory-sync.md` here — already
covered by the always-on `~/.claude/context/` bundles.)

## Verification gate (enforced)

`git commit` at the Workspace root is gated by
`.claude/hooks/check_verify_before_commit.py`, which runs
`_scripts/pre_commit_audit.ps1` and `_scripts/verify_workspace.ps1` and **blocks the
commit** if either fails (GEMINI.md §3). Run them yourself before declaring work
done. To bypass intentionally: append `[verify-override: <reason>]` to the commit
message, or set `$env:WORKSPACE_VERIFY_OVERRIDE=1` (both auditable). Commits whose
staged files are entirely under `sec-research/` are skipped — that subtree has its
own git hooks.

## Publishing privacy

Published work (the lab site under `site/` → garrettmanley.com) must be purged of
internal project names and repository identifiers (GEMINI.md §4). Corporate repos
(`Duracell*`, `malachite/`) are never touched, scanned, or read.
