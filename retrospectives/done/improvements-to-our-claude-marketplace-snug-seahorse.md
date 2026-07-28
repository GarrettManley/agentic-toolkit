# Retrospective: Claude 5 Modernization Sweep (marketplace + workspace assets)

**Plan:** `~/.claude/plans/improvements-to-our-claude-marketplace-snug-seahorse.md`
**Commit:** `7f362be` (`fix(orchestration): capitalize opus row to match sibling rows` — PR #62 head) + Workspace `97162b1`
**Date:** 2026-07-28

## Outcome

Full-lifecycle `/deliver` run: 3-agent research fan-out (marketplace inventory, workspace inventory, Sonnet 5/Opus 5 web research with official-vs-community sourcing) → FULL 9-agent adversarial plan review (10 CRITICAL-class findings fixed pre-execution) → 12 SDD tasks → whole-branch review + one fix wave → **PR #62** (20 commits: aether dead-hook fix, residual-Ollama sweep, agentic Claude 5 IDs + effort/caching, ambiguity-based routing + delegation caps, recall-safe review language at 5 sites, plugin-authoring conventions, `ci/lint-model-ids.py` gate, on-branch release bumps for 7 plugins) plus Workspace cleanup commit `97162b1` (context-file fixes with backups, `.ai/` retirement notes, `effort: low` pilot). Marketplace issue #61 tracks; closes on merge.

## What worked

- **9-agent adversarial plan review, again decisively** — 5 of 9 reviewers independently caught the lint denylist regex matching current `claude-haiku-4-5`; risk-rollback overturned the plan's release model (per-plugin CHANGELOGs are release.py-owned; `--apply` runs on-branch per ADR-0012, and post-merge `--apply` would ship nothing after a squash). Both would have been expensive live failures.
- **Whole-branch review at session model after down-routed per-task reviews** — caught cross-cutting model-fact errors no per-task reviewer could see (model-dependent cache floors; allowlist example not matching the marketplace's own blessed launch command).
- **Pristine-`main` worktree baseline to classify test failures** — three plugin suites failing locally reproduced identically on untouched `main` (Python 3.14 vs CI-pinned 3.12/3.13), converting a potential blocker into a documented pre-existing environment issue in minutes.
- **Research fan-out with official/community tagging** — the "no Haiku 5 exists" and "delete scaffolding, keep gates" corrections shaped the whole plan; the zero-deletable-scaffolding audit result (repo verification language is uniformly process-gate-shaped) was worth banking as a positive finding.
- **Fix-loop with implementer resume** — all four task-level fix rounds converged in one round each; the report-file-as-memory pattern made resumes cheap.

## Friction / bugs

- **Haiku implementer fabricated API facts on a "mechanical" doc task**
  - *What happened:* the Task 2 (windows allowlist) implementer wrote llama-server examples with port 8000 and Ollama's `/api/tags`/`/api/ps` paths — endpoints that 404 on a real llama-server.
  - *Root cause:* down-routed model filled a factual gap from association (8000 = the retired bridge port) instead of flagging the unknown; the dispatch supplied binary/model paths but not the API surface.
  - *How caught:* task reviewer (sonnet) verified against llama.cpp's official server README; the suspect claim was flagged in the review dispatch after the implementer's own summary contradicted known facts.
  - *Fix:* fix round 1 — port 8080, `/health` + `/v1/models`; later hardened again by the whole-branch review (`-m` + placeholders).
  - *Rule:* a doc task that states runtime/API facts is not mechanical — either supply every fact in the dispatch or route it up; and any implementer summary asserting a fact not present in its brief warrants a targeted reviewer pointer.
- **Research fact block carried two wrong/over-general claims into execution**
  - *What happened:* colon-rejection version cited as CC 2.1.214 (actual: 2.1.218) and a universal 512-token cache floor (actual: model-dependent 512/1024/4096).
  - *Root cause:* single-source summarization in the web-research report; the plan promoted it to "Verified Model Facts" without per-claim re-verification steps for harness claims.
  - *How caught:* Task 8's reviewer independently fetched the live changelog; the whole-branch reviewer cross-checked the claude-api skill.
  - *Fix:* both corrected on-branch (a6c1456, 53a72fc).
  - *Rule:* "verified" research facts feeding many edits deserve reviewer dispatches that explicitly re-fetch the primary source for the specific claim being encoded — the cited-URL habit made these cheap to re-check.
- **Plan's release-flow model was inverted until adversarial review**
  - *What happened:* the draft plan said "don't run `release.py --apply`; versions bump post-merge" — after a squash-merge, `--apply` would have found no conventional-commit subjects and released nothing.
  - *Root cause:* I modeled the release flow from the repo's CLAUDE.md summary instead of reading ADR-0012/release-process.md (the exact instinct: read the actual gate/tool before asserting behavior).
  - *How caught:* risk-rollback dimension read the ADRs.
  - *Fix:* plan rewritten; `--apply` ran on-branch (5b8ef7f); PR body carries the do-not-re-apply warning.
- **Combined pytest invocation produced a phantom failure signature**
  - *What happened:* re-running the three failing tests in one pytest command hit the known cross-plugin conftest collision and masked the real (pre-existing) failures.
  - *Rule:* in this repo, always reproduce plugin-test failures per-directory — a combined invocation's output is not evidence.
- **hb-64f widened** — the Workspace verify-override was needed again; the audit's prune misses `Career/` in addition to `claude-marketplace/` (evidence appended to the bead).

## Concrete improvements

- **`ci/lint-model-ids.py`** — this generation's rot gate (gen-4 dated IDs + Ollama-era refs), wired into verify.sh/CI with 6 tests; extend the denylist at gen-6 — done (PR #62).
- **hb-64f evidence** — prune both `claude-marketplace/` and `Career/` in `_scripts/pre_commit_audit.ps1` — follow-up (bead updated).
- **Post-merge checklist** (in PR body): `release.py --tag` on main, push tags, `/plugin` reinstall; do NOT re-run `--apply` — pending user action after checks go green.
- **Publish-chain side effect** — Task 11's `.ai/` commit regenerated `site/content/docs/toolkit/**` as unstaged diffs in the Workspace; harmless but dirty — pending user triage alongside the pre-existing resume-PDF diffs.
- **Effort-lever pilot** — `effort: low` on the one mechanical workspace agent (source-verifier) + authoring-doc guidance; broader adoption deliberately deferred until harness support is observed in practice — done (minimal by design).

Updates #61 (marketplace repo — closes via PR #62 merge). Updates hb-64f (evidence appended).
