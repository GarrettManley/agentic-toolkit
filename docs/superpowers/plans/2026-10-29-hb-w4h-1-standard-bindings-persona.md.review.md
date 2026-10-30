# Adversarial plan review — 2026-10-29-hb-w4h-1-standard-bindings-persona.md

Posture: FULL (triage: effort HIGH = 5 tasks; complexity HIGH = >8 files, two repos; uncertainty LOW = approved spec). Policy `auto` (no delivery.local.md at the Workspace root yet). Constitution: not bound (this plan creates it).
Dispatched: 6 dimensions (sonnet) + plan-skeptic, plan-feasibility-auditor, plan-scope-cutter. 86 raw findings, deduplicated to the 41 below (2 CRITICAL, 26 IMPORTANT, 14 MINOR; one IMPORTANT deferred with reason, the rest resolved in the revised plan). Resolution column records what the revised plan does.

## CRITICAL

| # | Finding | Resolution |
|---|---------|------------|
| C1 | Task 1/2/3 Workspace commits touch `docs/*` and `.ai/*`; `.git/hooks/post-commit` runs `publish.ps1` (Hugo + Firebase deploy of the **working tree**, which holds Garrett's uncommitted `site/**` edits). Live, non-revertable. (risk-rollback, feasibility) | **Resolved.** New Task 0 adds a `WORKSPACE_SKIP_PUBLISH=1` env valve to `publish.ps1` (auditable, reusable; mirrors the existing verify-override pattern). Every Workspace commit in this plan runs with it set. Verified the generators read only `.ai/adr` and `.ai/scripts`, so neither the standard nor `conventions.md` can reach the site. |
| C2 | The standard names internal projects and lives under `docs/`, which the hook "publishes" — Publishing-privacy violation. (feasibility) | **Resolved by evidence**, see C1: `docs/` is a deploy *trigger*, never deploy *content*. The privacy rule governs `site/`. Recorded in Global Constraints so no later reviewer re-raises it. |

## IMPORTANT

| # | Finding | Resolution |
|---|---------|------------|
| I1 | `_scripts/pre_commit_audit.ps1` descends into `claude-marketplace/` (8 tracked `.md` files contain literal `TBD`) and `mtga-companion/target`, so `check_verify_before_commit.py` denies every Workspace commit (open bead hb-64f). (feasibility-auditor) | **Resolved.** Task 0 extends the prune pattern with `claude-marketplace|mtga-companion|libs`; closes hb-64f. Baseline audit run added before Task 1. |
| I2 | Branch created over a dirty tree; no check that `git add` stages only intended files; no abort/rollback. (risk-rollback) | **Resolved.** Every commit step asserts `git diff --cached --name-only` equals the listed set; new "Abort and rollback" section with per-repo revert commands. |
| I3 | Task 2 Step 1 assumes `CLAUDE.md`'s pending diff is only the testing-strategy hunk. (risk, completeness, skeptic, auditor) | **Resolved.** Step runs `git diff CLAUDE.md` first and stops if any other hunk is present. |
| I4 | Nested-repo commits name no branch; mtga-companion is on `feat/phase-4-slice-2-followups`; home repo branch unstated; no cross-repo failure handling. (clarity, completeness, feasibility, auditor) | **Resolved.** Per-repo table: Workspace feature branch; System.Control `master` direct (its convention); mtga-companion via a throwaway worktree of `main`; home `main` untouched (AGENTS.md step dropped, see I12). Order-of-operations and failure table added. |
| I5 | sec-research binding: mixed commit runs the Workspace gate; sec-research hooks may block; from a root session the binding is never consulted. (risk, completeness, feasibility, skeptic) | **Resolved.** PT-3 blocks writes *outside* sec-research only; binding gets its own commit; body states it applies when Claude is launched inside `sec-research/`. |
| I6 | `constitution` path semantics undefined in the deliver skill; `test -f` proves existence only; CRLF breaks the loop (`core.autocrlf=true`). (feasibility, completeness, auditor) | **Resolved.** Binding body states "relative to this repo root (the directory holding `.claude/`)"; the loop strips `\r`; per-file value table replaces the ambiguous snippet. |
| I7 | Roleplaying file is gitignored: no history, no idempotence. (risk-rollback) | **Resolved.** Backup copy to the session scratchpad; insert only if the key is absent. |
| I8 | Marketplace binding rides the `feat(review)` commit in a public PR. (risk, completeness) | **Resolved.** Own `chore(deliver):` commit on the same branch; backticked path (not a link) so `check-doc-links` ignores it. |
| I9 | Checklist cited as "Task 4 step 3" (wrong step) and defined after Task 1 uses it. (clarity) | **Resolved.** Checklist moved to Global Constraints as the single source; Tasks 1 and 4 reference it. |
| I10 | "Byte-identical body" contradicts the standard's intro sentence; diff ignores CRLF. (clarity, feasibility, auditor) | **Resolved.** Claim restricted to the five numbered items; diff pipes through `tr -d '\r'`. |
| I11 | Persona shape drops `Pushback triggers` (validator-required); numbered lists elsewhere break the test. (feasibility, auditor, completeness) | **Resolved.** Keep the scaffold's bullet shape; Pushback triggers as bullets; `## Checklist` is the only numbered list; `tools: Read, Grep, Glob, Bash`; fill Source and Last updated. |
| I12 | AGENTS.md pointer pre-empts wave 2 and cites a non-existent path; spec lists only CLAUDE.md and conventions.md. (scope-cutter, skeptic, value) | **Resolved.** AGENTS.md step dropped from wave 1 (wave 2 owns it). Verbatim rule copy in CLAUDE.md dropped; link + tests-placement bullet kept. |
| I13 | `AGENTS_DIR` does not exist in `test_persona.py`; `count("\n1. ")` brittle. (clarity, completeness, feasibility, auditor) | **Resolved.** Test defines `AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"`, asserts the earned-abstraction phrase, and scopes the item count to the `## Checklist` section (exactly items 1-5). |
| I14 | CHANGELOG edits collide with `release.py`, which prepends sections itself. (completeness) | **Resolved.** Changelog steps removed. |
| I15 | Count strings live in more places than listed; `docs/skill-index.md` must be regenerated after Task 5's description change. (completeness, clarity, feasibility, auditor) | **Resolved.** Full site list in Task 4; `gen-skill-index --write` + staging in Task 5; zero-hit grep for `16 archetype|sixteen|16 agents` outside CHANGELOGs. |
| I16 | Persona's "when a constitution path is passed" has no producer: `adversarial-review-code` has no such argument and deliver step 10 never forwards it. (skeptic) | **Resolved.** Task 5 adds `--constitution <path>` to the skill Interface and Step 2, and a one-line forward in the deliver skill's step 10 (`feat(delivery)` commit). |
| I17 | No landing steps for the Workspace branch, nested repos, or the marketplace PR; persona not live until release + reinstall. (clarity, completeness, feasibility) | **Resolved.** "Landing" section: Workspace via the Hybrid menu (propose ff-merge), marketplace `gh pr create` against `main`, release/reinstall noted as the post-merge step that makes the persona live. |
| I18 | Spec acceptance "adversarial-review-code dispatches the persona" has no verification; anti-goal only substring-checked. (clarity, completeness, value, skeptic) | **Resolved.** Verification adds a pre-release behavioral run: a general-purpose agent primed with the new persona file reviews a seeded diff (one outward import + one single-implementation Protocol) and must flag the first and not the second. Live dispatch is deferred to post-release (noted). |
| I19 | Plan opens with deliverables, no problem statement or do-nothing baseline; code-reviewer overlap unaddressed. (value, skeptic) | **Resolved.** "Why" paragraph added to the header: today's reviews have no dependency-direction or earned-abstraction check (`code-reviewer` scores CLAUDE.md style), 12+ utility copies exist, the constitution slot is unbound; wave 1 is the gate waves 2-4 bind into. |
| I20 | System.Control's CLAUDE.md disclaims parent-workspace conventions, so the pointer is void there. (skeptic) | **Resolved.** Task 2 adds a one-line carry-over to `System.Control/CLAUDE.md` and `mtga-companion/CLAUDE.md`. |
| I21 | Audits may fail on the dirty tree for unrelated reasons; no baseline. (feasibility) | **Resolved.** Task 0 ends with both audits run on the current tree, output recorded. |
| I22 | `verify.sh` stages (lint-changelog, lint-model-ids, check-notice, check-doc-links) and `python3`/ruff availability unverified; pytest suites may collide. (feasibility, auditor) | **Resolved.** Task 4 Step 0 runs `verify.sh` on clean `main` as baseline; suites run separately. |
| I23 | `TBD` grep only on the standard; the audit scans every `.md` incl. `delivery.local.md`. (completeness) | **Resolved.** Grep extended to every touched `.md`. |
| I24 | gm-common binding (7th in spec) silently dropped. (completeness, clarity) | **Resolved.** Stated as deferred to hb-w4h.2. |
| I25 | Reviewer-persona shape mismatch: scaffold emits bullet form, not architect's H2 form. (my own pre-verification) | **Resolved**, see I11. |
| I26 | Standard/persona byte-identity is checked once at plan time across two repos with no durable gate afterwards. (skeptic) | **Deferred to hb-w4h.4** with reason: wave 4 already extends `verify_workspace.ps1` / marketplace `verify.sh` with sibling-path checks (`check-vendored-sync.py --source`); the checklist diff joins that mechanism there. Wave 1 pins the persona side in CI (Task 4 test) and the pair once (Task 5 diff). |

## MINOR (recorded; applied where one line suffices)

| # | Finding | Resolution |
|---|---------|------------|
| M1 | Reference layouts for four languages are speculative until such projects exist. (scope-cut) | Deferred to the builder's discretion: spec §6 asks for per-language layouts; keep them short (≤6 lines each). |
| M2 | Exemplar file paths rot. (scope-cut, completeness) | Kept (two verified present); Task 1 adds a step to `test -f` each. |
| M3 | Drop wave/tracker references from the durable standard §5. (scope-cut, skeptic) | Applied. |
| M4 | Shorten checklist item 4's utility list to "e.g." (scope-cut) | Applied. |
| M5 | Plugin-absent fallback has no precedent in the skill. (scope-cut) | Kept as one sentence; `review` named a soft prerequisite in Cross-references. |
| M6 | Binding body prose optional. (scope-cut) | Applied: body is the two required sentences only. |
| M7 | Scaffold expected output includes a Windows path repr and trailing sentence. (auditor) | Applied: expectation loosened. |
| M8 | `release.py --dry-run` "only" is an unverified prediction. (auditor, feasibility) | Softened to "includes review, docs, delivery". |
| M9 | Mixed-version window: docs references a persona an older review may lack. (risk) | Noted in Landing: release `review` before or with `docs`/`delivery`. |
| M10 | Kill switch for a bad standard. (risk) | Noted: remove the `constitution:` key. |
| M11 | Commit-count assertion fragile; plan/spec/review files untracked. (auditor, feasibility) | Verification counts commits by subject, and the plan + review + spec files are committed on the branch in Task 0 (count updated). |
| M12 | `model_used` hard-coded in conventions frontmatter. (clarity) | Applied: "the executing model". |
| M13 | Public-name grep should include `gm-common`, `hb-w4h`. (feasibility) | Applied. |
| M14 | Retrospective placeholder lacks tracker closeout. (completeness) | Applied: Landing ends with `bd close hb-w4h.1` + `bd close hb-64f`. |
