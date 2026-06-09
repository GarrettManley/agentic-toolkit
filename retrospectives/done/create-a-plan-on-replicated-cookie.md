# Retrospective: Harness + marketplace quality pass (audit 2026-06-09)

**Plan:** `~/.claude/plans/create-a-plan-on-replicated-cookie.md`
**Commit:** marketplace `f727b1b..d937f25` (9 commits, 2 releases); workspace `1250ebf`,
`f49fc5e`; home `ba8d349`; System.Control `d0ee3ff`
**Date:** 2026-06-09

Issue state: Closes hb-9hv (epic, all 17 children), Closes hb-28u.6 (CI decision),
Updates hb-28u.

## Outcome

Full three-phase pass executed same-day. Phase 1: hook-failure logging
(`~/.claude/logs/hooks.log`), nightly steward registered + smoke-tested, shadow context
slimmed to pointers, `.ai` truth-base re-verified, two stale retrospectives backfilled.
Phase 2: GitHub Actions CI (green ×4 runs), vendored hook-lib made byte-identical with a
`--fix` sync gate (repo-root pytest fixed: 295→0 collection errors), 51 evidence tests,
frontmatter lint. Phase 3: drift_check staleness extension (stewardship@0.3.0), generated
skill index (23 skills/4 agents, drift-gated), README/coupling/HMAC docs,
orchestration@0.1.1. Two optional tasks skipped on measured evidence (dispatcher: risk vs
~1s/edit; token trim: ~150 tokens available vs 2k total).

## What worked

- **Audit → plan-agent correction loop.** The Plan agent grep-verified audit findings and
  killed four before execution (regex false-positive claim, "build new drift automation"
  when `register_nightly.ps1` already shipped, stale retro slugs, untestable review
  plugin) — and found the broken repo-root pytest collection the audit missed.
- **Ground-truth before fixing "drift".** `ollama list` showed *both* sides of the
  hardware-profile disagreement were wrong (`deepseek-r1:7b` is what's installed);
  fixing canonical + AGENTS.md + orchestration tiers in one pass killed the drift class,
  not just the instance.
- **Byte-identity over clever dedup.** Deriving the env prefix from the hook-id namespace
  (~10 lines) made vendored copies `filecmp`-comparable — no normalization logic, no
  build step, plugins stay cache-installable.
- **Hard-block hooks earned their keep on their own repo.** GateGuard forced caller/data
  audits on every first-touch; the TODO hook caught `todo-issue` inside a docstring; the
  secret-scan constraint produced scanner-clean concatenated test fixtures.

## Friction / bugs

- **GateGuard blocks one edit inside a parallel batch**
  - *What happened:* batched Edits where some landed and the gate blocked others — twice
    leaving a file referencing an import that the blocked edit was meant to add.
  - *Root cause:* the gate is per-tool-call; parallel batches interleave with its
    present-facts-then-retry protocol.
  - *How caught:* immediately, by reading the batch results.
  - *Fix:* completed the blocked edits next call.
  - *Rule:* under fact-forcing gates, don't split one logical change (import + usage)
    across parallel tool calls — make the first-touch edit solo, then batch.
- **`release.py` doesn't release refactors**
  - *What happened:* plan assumed "patch bumps via release.py" for the vendored-lib
    refactor; dry-run said nothing release-worthy.
  - *Root cause:* bump map is breaking/feat/fix/perf only — by design.
  - *Fix:* deferred shipping to each plugin's next natural release (old cache copies are
    behavior-identical); gotcha recorded in the repo CLAUDE.md.
  - *Rule:* check the release tool's commit-classification before promising version bumps
    in a plan.
- **PowerShell `gh run watch` / CIM calls stall in background tasks** — two background
  shells never returned output; re-running foreground (or via Bash with `timeout`) worked.
  Don't park verification on a backgrounded PowerShell that might never notify.

## Concrete improvements

- **Nightly steward now actually runs** (was shipped-but-never-registered) and 0.3.0 adds
  the staleness check that would have caught this audit's 71/76-day frozen files months
  earlier. Status: done, live tonight at 03:00.
- **CI converts every local gate into a push-time guarantee** — version drift, vendored
  sync, frontmatter, skill-index, 320+ tests. Status: done, green.
- **Follow-up (residual):** 5 workspace `.ai/context/` subdir files remain frozen at
  2026-03-25 with 3 failing verification_cmds (e.g. sandbox health endpoint) — flagged by
  the new tool, deliberately out of this pass's scope. Re-verify when next touching the
  orchestration/maintenance subsystems.
