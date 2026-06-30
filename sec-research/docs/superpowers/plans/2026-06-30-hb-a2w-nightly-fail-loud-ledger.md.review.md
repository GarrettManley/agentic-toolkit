# Adversarial Plan Review — hb-a2w nightly fail-loud ledger

Plan: `2026-06-30-hb-a2w-nightly-fail-loud-ledger.md`
Reviewers: 6 dimensions (feasibility, value-justification, clarity, completeness, risk-rollback, scope-cut) + 3 archetypes (plan-skeptic, plan-feasibility-auditor, plan-scope-cutter), all run in parallel against the plan and the live codebase.

## CRITICAL

- **Scope excludes the actual production nightly path, which has the identical bug, live.** (plan-skeptic, completeness, value-justification — corroborated 3x; independently confirmed by orchestrator: `sec-research-nightly` is a registered Windows Scheduled Task in `Ready` state, `run_nightly.ps1` invokes `nightly.py` with zero flags → `run_unattended()`, which has no journal/checkpoint at all and the same `generate_hypotheses` swallow-and-continue call.) The plan as written only protects the rarely-used manual `--supervised` mode (used exactly once, for hb-322). Either justify scoping to supervised-only, or extend the fix to cover both entry points — a simpler design exists: both `run_unattended` and `run_supervised` already call the shared `stage_briefing()` (nightly.py:151-187), which already has a "Ledger health" section. Counting `HYPOTHESIZE_FAILURE_EVENTS` there covers both paths with a smaller diff than the `_halt`-signature change.

- **`slug` is not the per-recon-item identifier — the plan's own acceptance criterion isn't met.** (clarity, verified independently by orchestrator against `scripts/recon/recon_item.py:51`) `slug` is the program-level scope slug, constant across every recon item/asset for the whole run. The true per-item identifier is `item["asset"]["identifier"]`, captured in the ledger event only for `hypothesis-llm-unavailable` (`generate.py:135-136`) and never for `hypothesis-parse-error` (`generate.py:142`, only `slug=slug`). As implemented, two different failing assets in the same program are indistinguishable in both the stderr warning and the journal — "the operator must be told recon item N's LLM call failed" is not actually satisfied.

## IMPORTANT

- **Task 2 Step 6's "verification gate runs automatically" claim is false for this commit.** (feasibility, risk-rollback, plan-feasibility-auditor, scope-cut — corroborated 4x) `check_verify_before_commit.py` explicitly skips when every staged path is under `sec-research/`; `.git/hooks/` has no installed `pre-commit`/`commit-msg` at all, so sec-research's own G-1/G-2/G-4 hooks are also inert for this repo state. The manual pytest re-run (Steps 1-5) is the *only* real check before this lands on master — not a redundant echo of an automatic gate.

- **A mid-stage exception in `stage_hypothesize` drops already-logged failures silently.** (risk-rollback, plan-feasibility-auditor — corroborated 2x) `generate_hypotheses`'s own docstring states `ScopeViolation` propagates uncaught. If item N raises after items 1..N-1 already logged transient failures, the exception unwinds before `_hypothesize_failures_since`/`_halt("hypothesize", ...)` ever runs — the checkpoint, and the new warning, are never written. This is exactly the partial-failure case the plan exists to surface.

- **No `## Retrospective` section.** (completeness) Sibling plans in the same directory carry one, and the user's `check_plan_retrospective.py` PreToolUse hook on `ExitPlanMode` enforces it.

- **Do-nothing baseline and "generalized fix" justification are asserted, not established in the plan body.** (value-justification, 2 findings) The masking pattern already happened twice live during hb-322, caught only by a final whole-branch review, not by design — that cost should be stated explicitly, not left in a code docstring. Separately, the specific hb-322 trigger (inherited MCP tools) is already fixed (commit `a0f5b8b`); the plan should name what *other* transient-failure classes (provider rate limits, network blips) it's actually still guarding against.

- **File Structure summary contradicts Task 1's own insertion-point instructions.** (clarity) "under the existing Supervised flow section" (File Structure, line 24) vs. "between CLI argument wiring and Supervised flow" (Task 1) are mutually exclusive anchors in the real file.

## MINOR

- **"Five other `_halt(...)` call sites" should be "four."** Duplicated independently by feasibility, clarity, completeness, plan-feasibility-auditor, and risk-rollback (5 of 9 reviewers) — `run_supervised` has 5 total `_halt` call sites; excluding the hypothesize one being modified leaves 4 (recon:314, verify:329, triage:344, draft:353).
- Line-range citations for `_today()` (81-83 vs 82-84) and `run_unattended` (190-219 vs actual 190-239) disagree across the plan's own passages — reconcile to one number per claim (feasibility, clarity, completeness, plan-feasibility-auditor).
- `entry_id`/`slug` `?` fallbacks in `failure_desc` guard a state the plan's own cited call sites guarantee cannot occur (`ledger.append_event` always sets `entry_id`; both relevant `generate.py` call sites always pass `slug=`) — drop the fallbacks or justify them (scope-cut, 2 findings).
- No explicit rollback-path statement for the direct-to-master commits, even though the change is additive/backward-compatible and trivially `git revert`-able — state it explicitly for a future incident responder (risk-rollback).
- A concurrent `run_unattended` (cron) run writing to the shared ledger during a manual `--supervised` run could misattribute the other run's failure events to this run's checkpoint — document or scope the diff to this run's own writes (risk-rollback). Likely moot once the CRITICAL cron-path finding is resolved by moving detection into the shared `stage_briefing()`.
- `from .paths import LEDGER_PATH` quote is incomplete — actual import is `from .paths import LEDGER_PATH, SUBMISSIONS_DIR` (clarity).
- No final consolidated "## Verification" section distinct from per-step pytest commands, unlike sibling plans — stylistic drift, the integration tests functionally serve this role already (completeness).
- Goal's opening sentence leads with the fix mechanism before stating the problem — reorder (value-justification).
