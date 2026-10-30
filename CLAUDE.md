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

## Hook federation router (Workspace root)

- `PreToolUse|PostToolUse|Stop|UserPromptSubmit` → `.claude/hooks/hook_router.py` (federation router): auto-discovers nested projects' own `.claude/settings.json` (depth-1; `Duracell*`/`malachite` hard-excluded) and replays their hooks from this root, so e.g. `sec-research/`'s governance hooks fire without relaunching Claude inside the subdir. Config: `.claude/hooks/hook-router.config.json` (`enabled` kill-switch, `ignore` list, `timeout_seconds`). Fail-open on router faults; a child's exit-2 still blocks. See `.claude/docs/specs/2026-06-20-workspace-hook-federation-router-design.md`.

## sec-research/ — hooks only fire when launched from inside it

`sec-research/` enforces **17 hard-block rules** (scope-bounding, evidence
discipline, secret-scan, submission gate) via `sec-research/.claude/settings.json`,
whose hook paths resolve through `${CLAUDE_PROJECT_DIR}`. That variable only points
at `sec-research/` when **Claude is launched from inside that directory**.

**With the federation router active (registered above), `sec-research/`'s hooks now
also fire from a Workspace-root session.** For deep recon / evidence / findings work,
launching from inside `sec-research/` is still recommended (native load; no router
overhead). Read `sec-research/CLAUDE.md` (the canonical orientation doc + hook map)
before sec-research work in either context.

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

## Testing strategy (all projects under Workspace/)

Follow the Practical Test Pyramid (https://martinfowler.com/articles/practical-test-pyramid.html).
Garrett set this as the rule for every project here (2026-10-26). The operative points:

- **Shape.** Many small, fast unit tests; fewer narrow integration tests; very few end-to-end
  tests. "Write tests with different granularity" and "the more high-level you get the fewer
  tests you should have."
- **Unit tests** test observable behaviour through the public interface (given inputs, expect
  result), never the calls between collaborators and never private functions; if a private
  function wants a test, split it into its own unit. Solitary or sociable per case. No tests
  for code without conditional logic.
- **Integration tests** cover one external integration point each (database, filesystem,
  process, service), with the others doubled; every serialisation boundary gets one. Local
  dependencies only; never the production system or the production data store.
- **Contract tests** at service boundaries are consumer-driven (the consumer writes what it
  needs; the provider runs them).
- **End-to-end** covers only the most valuable journeys and is expected to be slow and flaky;
  acceptance checks sit at the lowest level that can express them.
- **No duplication across levels.** "If a higher-level test spots an error and there is no
  lower-level test failing, you need to write a lower-level test." "Push your tests as far down
  the test pyramid as you can." Delete a higher-level test that adds no confidence beyond the
  lower ones; keep it only if it genuinely adds confidence.
- **Test code is production code.** Arrange/act/assert, one condition per test, readable over
  DRY (Rule of Three before extracting helpers).
- **Pipelines** order stages by speed and scope, fast feedback first.

Applied to the agentic workflow: every per-task test design names the level of each case and
justifies any case above unit level; test-strategy reviews reject a case at the wrong level; a
fixture or end-to-end gate that catches a bug with no failing unit test is a review finding
(write the unit test) rather than a pass.

## Architecture standard (all projects under Workspace/)

The SOLID + Clean Architecture standard lives at [`docs/standards/solid-clean-architecture.md`](docs/standards/solid-clean-architecture.md). `/deliver` binds it as `constitution`, and `review:architecture-conformance` measures diffs against its reviewer checklist.

- **Tests live in sibling test files, never inline in implementation files** (all languages; in Rust, a `#[cfg(test)] mod tests;` declaration in the source points at a sibling `tests.rs`).
