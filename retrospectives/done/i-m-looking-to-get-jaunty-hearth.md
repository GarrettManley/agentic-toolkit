# Retrospective: Node governance arc (slice-1 stabilization → Node management → hardening)

**Plan:** `~/.claude/plans/i-m-looking-to-get-jaunty-hearth.md`
**Commit:** `df8dd29` (`build(graphs): regen ts-module-graph on Node 24 + engine-strict gate`)
**Date:** 2026-06-09

> Note on slug reuse: this one plan slug hosted **three** sequential, related plans (last-writer-wins on the
> plan file). All three completed. This retro covers the arc.
> 1. **Slice-1 stabilization** (#149/#137/#150) — aether-cli lifecycle, world-map flake, depcruise/graph guard.
> 2. **Manage Node on this machine** — Current→LTS channel swap + engine-strict + footprint migration.
> 3. **Harden the Node setup** — winget channel pin + dangling-link removal.

## Outcome

Root-caused #149 as a *toolchain-governance* failure (machine on the winget **Current** channel → EOL'd Node
23.9 → depcruise 17 hard-aborts → silently-empty module graph) rather than a code bug. Moved the machine to
**Node 24.16 LTS**, added a three-layer drift defense (build-time `gen-ts-graph.mjs` guard, install-time
`engine-strict`, CI pin), hard-pinned the Current channel in winget, and removed dangling cruft. The slice-1
branch (`chore/slice1-stabilization`, 5 commits) is reviewed, Node-24-green, and one sign-off short of merge;
`~/AGENTS.md` and the slice-1 #149 verification (graph regen + arch-rules + engine-strict, `df8dd29`) landed.

## What worked

- **Advisor-driven scope correction.** The advisor caught that the Node-management plan had silently absorbed
  the slice-1 *landing* (duplicate `Closes #149/#137/#150` across two plan artifacts). One AskUserQuestion
  re-scoped it to Node-only — the single highest-leverage course-correction of the arc.
- **Empirical-over-assumed verification.** winget's dual-ID/shared-ARP pin behavior is under-documented (open
  bugs #5244/#5879), so the pin was *applied then proven* (`pin list` Blocking, `winget upgrade` no 26.x, LTS
  id unpinned) rather than trusted. Same instinct decomposed the slice-1 tail by its Postgres dependency —
  closing #149 on static analysis (graph + arch-rules), not gating it on a DB-dependent full suite.
- **Live-machine audit before a destructive step.** Auditing the Node footprint (8 global CLIs, `claude.exe`
  native, WSL's separate node) before the `winget uninstall` turned a scary system-wide swap into a bounded,
  reversible one.
- **GateGuard fact-forcing** surfaced the real blast radius on each first-touch (AGENTS.md importers, .npmrc
  consumers) — friction that paid for itself.

## Friction / bugs

- **winget can't elevate from a non-interactive tool**
  - *What happened:* `winget uninstall` from the PowerShell tool failed with MSI **1603**.
  - *Root cause:* the tool runs `-NonInteractive`; the package is machine-scoped → needs UAC, which can't be
    granted headlessly. MSI rolled back cleanly (verified node still 23.9 intact).
  - *How caught:* non-zero exit + immediate state re-check.
  - *Fix:* user ran the two `winget` commands via the `!` prefix (interactive session → UAC dialog).
  - *Rule:* machine-scoped winget install/uninstall is a user `!`/admin step, never a tool step; tool-side is
    verification only.
- **Stale Current-channel package install (root cause of #149)**
  - *What happened:* the machine tracked `OpenJS.NodeJS` (Current), landing EOL Node 23.9.
  - *Root cause:* the Current winget package auto-tracks the newest line (odd/non-LTS included).
  - *Rule:* on Windows, install `OpenJS.NodeJS.LTS`, never `OpenJS.NodeJS`; pin the Current ID blocking.
- **Recurring Prettier churn on committed files**
  - *What happened:* 3 already-committed test files kept re-appearing as modified (single→double quotes,
    4→2 indent) — twice across sessions (also a stashed batch on gateway files).
  - *Root cause:* committed files weren't Prettier-conformant (lint-staged scopes formatting to `src/**`, not
    `tests/**`); a format-on-save reformats them in the working tree.
  - *How caught:* `git diff --ignore-all-space` still showed non-whitespace deltas (quote chars, parens) — the
    fingerprint of a formatter, not logic.
  - *Fix:* `git checkout --` to drop (cosmetic, zero-logic).
  - *Rule (generalizable):* when committed files repeatedly re-dirty with quote/paren/indent-only deltas,
    suspect a formatter scope gap — don't debug it as logic; either conform the files or widen lint-staged.
- **`.remember/remember.md` silently emptied mid-arc**
  - *What happened:* the durable handoff was wiped (streaming-memory rotation); SessionStart injected a stale
    snapshot while the live file was empty.
  - *Fix:* rewrote a dual-plan handoff; kept it updated as tracks completed.
  - *Rule:* re-read `remember.md` from disk before trusting the injected snapshot on resume.

## Concrete improvements

- **winget blocking pin** on `OpenJS.NodeJS` — done (valve: `winget pin remove --id OpenJS.NodeJS`).
- **`engine-strict=true`** in `Roleplaying/.npmrc` — committed (`df8dd29`); install-time #149 gate.
- **`.nvmrc`=24 + `engines` + CI pins + `gen-ts-graph.mjs` fail-loud guard** — committed on the slice-1 branch.
- **`~/AGENTS.md`** runtime line corrected to Node 24 LTS — committed (home repo `1f2a132`).
- **Dangling `roleplaying` global npm link** removed — done.
- **Deferred (documented):** WSL `node v18` (EOL) upgrade; a node-version drift sentinel; the slice-1
  merge+push (awaits user sign-off).
