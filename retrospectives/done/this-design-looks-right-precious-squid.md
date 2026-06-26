# Retrospective: Complete every proposed/TODO capability in claude-marketplace (Wave 1: W0 + D1)

**Plan:** `~/.claude/plans/this-design-looks-right-precious-squid.md`
**Commit:** `752d0b8` (`chore(release): learning@1.3.0`)
**Date:** 2026-06-25

## Outcome

Shipped the first wave of the marketplace feature-completion program. **D1** added the `learning` plugin's Phase 2c (`/instinct-detect`, Claude-driven correction/preference detection) and Phase 3 instinct lifecycle (`/prune`, `/promote`, `/evolve`) on a new schema foundation (`last_reinforced`, `is_machine_source()`, atomic reinforcing writes) — 41 new tests, 225 passing, 98% repo coverage, released as `learning@1.3.0` via PR #9. **W0** recorded the Phase-5 plugin compliance audit, cut aether 1.1.1 in the root changelog, backfilled two missing release tags, and merged the three dependabot PRs. Future waves D2–D5 are tracked as issues #5–#8.

## What worked

- **`/adversarial-review-plan` before execution** — the single highest-leverage step. Its feasibility-auditor (reading actual source) caught two factual errors and a real bug *before any code was written* (see Friction). Worth the agent spend every time a plan asserts how existing tooling behaves.
- **TDD red-green per module** — every module (`detect`, `prune`, `promote`, `evolve`, schema) got a failing test first. The schema work surfaced the `is_machine_source` overwrite-policy bug as a concrete RED rather than a latent runtime surprise.
- **Brainstorming `AskUserQuestion` gates** — the "build everything" / "Both engine" / "per-plugin specs" decisions scoped the program up front; the review then re-confirmed two trims (cut Path B, cut `/evolve --emit-artifacts`) the user accepted. Cheap decisions, large scope impact.
- **Up-front Explore agents for the wiring map** — discovering the `instinct_cli.py` dispatcher pattern, the schema's lack of a source allow-list, and the absence of any existing HTTP/LLM client made the plan reuse-aware and correctly flagged the llama-server backend as an architectural first.
- **snapshot-before-`--apply` + dry-run-default** for the destructive Phase-3 commands — and a single `is_machine_source()` predicate as the one source of truth for overwrite/decay eligibility, which closed the write/prune drift the review flagged.

## Friction / bugs

- **Plan asserted wrong `release.py` / version facts**
  - *What happened:* The plan said to run `release.py` to "cut aether 1.1.1" and to have it update the root changelog.
  - *Root cause:* I modeled `release.py`'s behavior from memory instead of reading it; aether was already `1.1.1` (so a bump would emit 1.1.2), and per ADR-0008 `release.py` never touches the root changelog.
  - *How caught:* `/adversarial-review-plan` (feasibility-auditor, by reading the source) — two CRITICAL findings.
  - *Fix:* Rewrote W0 to *tag* aether-v1.1.1 and treat the root changelog as a manual edit.
  - *Rule:* Adversarially review any plan that claims how existing tooling behaves; the auditor must read the tool, not the plan author's memory.

- **`write_instincts` overwrite-policy bug (latent)**
  - *What happened:* The plan's "re-derivation reinforces detected instincts" wouldn't have worked.
  - *Root cause:* `write_instincts` only overwrote `auto-`-prefixed sources, so `claude-detected` would be preserved as if human-authored.
  - *How caught:* review (feasibility dimension) cross-read `synthesize.py:180`.
  - *Fix:* Introduced `is_machine_source()` and switched both the writer and prune to it.
  - *Rule:* When adding a new enum value that an existing predicate gates on, audit every `startswith(...)`/membership check that consumes it.

- **Missing release tags (`aether-v1.1.1`, `learning-v1.2.0`)**
  - *What happened:* `release.py --dry-run` proposed an unexpected aether bump and bundled an old learning feature into the changelog.
  - *Root cause:* Prior releases bumped `plugin.json` but the tags were never pushed (a pre-existing hygiene gap), so the "since" baseline was stale.
  - *How caught:* `release.py --dry-run` after `git fetch --tags` returned nothing new.
  - *Fix:* Backfilled annotated tags at the correct commits before applying.
  - *Rule:* Treat a surprising `release.py` bump as a missing/stale tag first (the documented gotcha), and verify the tag exists for every shipped version.

- **`gh` token lacked `workflow` scope**
  - *What happened:* Merging dependabot #3 (edits `.github/workflows/ci.yml`) was refused; #1/#2 slipped through before the wall bit.
  - *Root cause:* The OAuth token had `repo` but not `workflow`; GitHub requires `workflow` to merge PRs touching workflow files.
  - *How caught:* GraphQL error at merge time.
  - *Fix:* User ran `gh auth refresh -h github.com -s workflow`; then #3 merged.
  - *Rule:* Before merging dependabot/CI PRs via `gh`, expect a `workflow`-scope requirement for any PR under `.github/workflows/`.

- **Environment gotchas (minor)**
  - Standalone `jq` is not on PATH here — my background waiter script silently failed; use `gh ... --jq` (gh's built-in) instead.
  - The repo default branch is `main`, not `master`; the first `gh pr create` failed until `--base main`.
  - A user-level `discipline` `frontmatter_lint` hook mis-fired on the marketplace's plain-markdown `docs/` — cosmetic cross-repo collision; no bogus frontmatter added.

## Concrete improvements

- **`retrospectives/pending/` is not gitignored** — the skill says it should be; add it to the Workspace `.gitignore`. Follow-up.
- **Phase 2c Path B (llama-server detection backend)** — deferred this wave; revisit when a concrete headless/nightly consumer exists. Tracked in the plan appendix.
- **Waves D2–D5** — evidence scope-binding hook, review persona-evolution, stewardship horizon-scan + briefing renderer — each begins its own brainstorm→spec→plan cycle (issues #5–#8). Pending.
- **PR #9** awaits the user's review/merge (sole-maintainer review gate; not admin-bypassed by design). Pending.
