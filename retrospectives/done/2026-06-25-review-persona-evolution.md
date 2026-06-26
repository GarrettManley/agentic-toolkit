# Retrospective: Review Persona-Evolution Automation (D3)

**Plan:** `~/.claude/plans/2026-06-25-review-persona-evolution.md`
**Commit:** `2400c31` (`feat(review): persona-evolution automation (D3, #6) (#13)`)
**Date:** 2026-06-25

## Outcome

Shipped `review@1.2.0` to the public marketplace: `/review-evolve <slug>` now automates the plugin's manual *Post-Cycle Update Protocol*. Claude derives a cycle's per-persona Caught/Missed/Hallucinated catches from the in-context review report and authors refined full-persona rewrites; the new `review_cli.py evolve` ingester validates each rewrite's structure (frontmatter keys, required sections, name match) and atomic-writes it, dry-run by default. This is the `review` plugin's first `scripts/` + `tests/` (two modules, 21 tests, 100% line coverage) and its first ADR (0009). Delivered as deliverable D3 of epic `hb-28u`; PR #13 squash-merged; the `review-v1.2.0` tag was reconciled to the squash commit so `release.py` sees no spurious bump. New-archetype scaffolding was deferred to #12.

## What worked

- **`adversarial-review-plan` (9 agents) earned its keep** — it caught three repo-verified bugs the plan would otherwise have shipped (see Friction). The `docs:plan-skeptic` and `docs:plan-feasibility-auditor` archetypes produced the highest-value findings; the dimension `Explore` agents returned clean structured findings.
- **Brainstorming gate before planning** — locking catch-capture / edit-scope / scaffolding / safety as explicit AskUserQuestion decisions meant the adversarial pass debated *execution risk*, not *intent*, and the one premise the review reopened (the ledger) was a fast, clean pivot.
- **TDD red-green per module** → 100% coverage with no scramble; the `# pragma: no cover` lines were decided up front (atomic-write cleanup, `main` fallthrough, `__main__`).
- **The dev clone's own pre-commit `verify.sh` gate** ran all 10 checks on every commit, so lint/frontmatter/doc-link regressions surfaced at commit time, not at PR CI.
- **Mirroring learning's `command = judgment / script = mechanical` split** gave a proven shape to copy, keeping the non-deterministic reasoning out of the tested Python.
- **`gh ... --body-file`** cleanly dodged the `discipline:gateguard` text-match false-positive again (issue/PR bodies containing `git checkout`/`--force` prose).

## Friction / bugs

- **Plan assumed CI gates cover `commands/*.md` — they don't**
  - *What happened:* Plan steps verified `/review-evolve` would appear in `gen-skill-index` and pass `lint-frontmatter`. Both gates glob only `skills/*/SKILL.md` + `agents/*.md`; a command is invisible to them, so those verification steps could never pass.
  - *Root cause:* Pattern-matched from the D1 learning plan (which added commands and ran `gen-skill-index --write`) without checking the gate's actual globs.
  - *How caught:* Adversarial feasibility agents, verified against `ci/gen-skill-index.py` / `ci/lint-frontmatter.py` source.
  - *Fix:* Removed the impossible steps; the plan now states commands are un-indexed/un-linted (manual flag-match self-check only).
  - *Rule:* Before asserting a CI gate covers a new file type, read the gate's glob — don't infer coverage from a sibling plan.

- **Default write target resolved to the read-only install cache**
  - *What happened:* The CLI's default `--agents-dir` was the shipped `plugins/review/agents/`. For anyone not in the dev clone, `${CLAUDE_PLUGIN_ROOT}/agents` resolves to the read-only install cache, so `--apply` would fail — and it contradicted the plugin's own guidance that adopter refinements stay in project-local `.claude/agents/`.
  - *Root cause:* Defaulted to a plugin-relative path by analogy, without reasoning about install-cache resolution or the plugin's stated project-local convention.
  - *How caught:* `docs:plan-skeptic` + `docs:plan-feasibility-auditor`, cross-checked against `reviewer-personas/SKILL.md` L16/L45.
  - *Fix:* Default to cwd-relative `.claude/agents/`; the maintainer passes `--agents-dir plugins/review/agents/` explicitly.
  - *Rule:* A plugin script's default *write* target must be cwd/project-local, never `${CLAUDE_PLUGIN_ROOT}`-relative — the plugin root is read-only at runtime.

- **Subagent reported a missing release tag from stale refs**
  - *What happened:* The feasibility-auditor flagged "no `review-v*` tag exists" as a release-correctness blocker. The tag did exist on origin; the agent inspected `.git/packed-refs` before any `git fetch --tags`.
  - *Root cause:* Subagent read local refs without fetching.
  - *How caught:* Step 0.3 re-checked after `git fetch --tags` — tag present, ancestor of HEAD.
  - *Fix:* Plan was written defensively ("if absent, create at the 1.1.0 commit"), so the false alarm cost nothing; no tag work was needed.
  - *Rule:* A subagent asserting git tag/remote state must `git fetch` first or explicitly caveat that its view is local-only.

- **Per-plugin coverage command would have failed the global gate**
  - *What happened:* `coverage report --fail-under=90` after running only `plugins/review/tests` counts all of `ci/` + every other plugin at ~0% (`.coveragerc` `source = ci, plugins`) → fails.
  - *Root cause:* Conflated a per-plugin run with the repo-wide combined gate CI uses.
  - *How caught:* feasibility-auditor.
  - *Fix:* Local check scoped with `--include='plugins/review/scripts/*'`.
  - *Rule:* For a local per-plugin coverage check under a repo-wide `source`, scope with `--include`; the unscoped `--fail-under` is only valid over the full combined suite.

- **Plan-mode tracks one plan-file path; a dated plan diverges from it**
  - *What happened:* ExitPlanMode saved/echoed the *old* D1 umbrella plan (`this-design-looks-right-precious-squid.md`) as "the approved plan," while the real D3 plan lived at a dated path. No pending retro marker was created for the D3 slug.
  - *Root cause:* Plan mode binds to a single tracked plan-file; writing a new dated file (correct, to avoid clobbering the completed D1 record) leaves the marker/echo pointing at the stale path.
  - *How caught:* Noticed the mismatch in the approval echo; `/plan-completion` then `/plan-retrospective` were pointed at the dated path explicitly.
  - *Fix:* Kept the D3 plan at its dated path, wrote the retro done-file directly (marker step optional per the skill).
  - *Rule:* When plan-mode's tracked file is a *prior, completed* plan, write the new plan to a fresh dated path, accept the marker won't auto-create, and drive completion/retro by explicit path.

## Concrete improvements

- **Dropped the catch-ledger** (ledger+fallback → derive-from-report) — removed a whole module (`catches.py`) + its tests; the in-context report already supplies the personas and Triage buckets. Done (user pivot during review).
- **`last_updated_line` given a real job** — the ingester now warns when a rewrite leaves the `**Last updated:**` line unchanged, instead of the helper being dead code. Done.
- **Tag reconciliation done inline** — re-pointed `review-v1.2.0` to the squash commit immediately after merge and verified `release.py --dry-run` is clean, pre-empting the recurring squash-orphan (the D6 #11 pattern) rather than leaving it to fix later. Done.
- **New-archetype scaffolding** — filed as #12 with a concrete done-bar (scaffold a valid persona from `templates/persona-stub.md`). Follow-up.
- **ADR-0009 as the single design record** — folded the would-be standalone spec into the ADR, avoiding a cross-repo orphan path (`docs/superpowers/` doesn't exist in the marketplace tree). Done.
