# Adversarial Plan Review — Discovery-Loop Validation & Stage 7 (huntr) Wiring

**Plan reviewed:** `docs/superpowers/plans/2026-07-01-discovery-loop-validation-plan.md`
**Date:** 2026-07-01
**Posture:** FULL (deliver's step-5 triage: Effort HIGH — 5 `## Task` headings; Complexity
HIGH — 13 files touched, a JSON schema change, and real external side effects in Tasks 2/4)
**Agents:** 6 dimensions (feasibility, value-justification, clarity, completeness,
risk-rollback, scope-cut) + 3 archetypes (plan-skeptic, plan-feasibility-auditor,
plan-scope-cutter), all run in parallel, each independently verifying claims against the
actual current source rather than trusting the plan's own text.
**Verdict: fixes required before execution.** Several CRITICAL findings — a vetting
criterion that references a field the recon pipeline structurally cannot produce, a wrong
CLI flag that silently breaks the Task 2→Task 4 validation chain, a real test bug (wrong
sys.path, missing ledger isolation), a security fix that doesn't close its actual threat
model, and speculative scope three independent reviewers converged on cutting. All are
resolved below; the plan is amended in place rather than re-reviewed from scratch.

---

## CRITICAL

```
[CRITICAL] (feasibility + clarity, independently confirmed) — Task 4 Step 2 vetting-bar
criterion #3: "direct (appears in the resolved lockfile's top-level dependencies...)" →
`scripts/recon/deps.py`'s `Closure.direct` is hard-coded to `[]` in v1 ("v1 does not
distinguish direct from transitive deps") — recon.json cannot answer this question via the
automated field the plan describes inspecting. FIXED: Task 4 Step 2 rewritten to specify a
manual procedure (open package.json/package-lock.json directly) instead.

[CRITICAL] (feasibility + clarity, independently confirmed) — Task 4 Step 3: "python
scripts/nightly.py --supervised --provider claude" → `scripts/llm/client.py` treats
"claude" and "claude-cli" as distinct providers; Task 2 validates claude-cli specifically,
so running Task 4 against plain "claude" means Task 2's whole measurement never informs the
provider Task 4 actually uses. FIXED: changed to `--provider claude-cli`.

[CRITICAL] (clarity + risk-rollback, independently confirmed) — Task 4 Step 2→3: "delete or
leave the loaded-but-unused scope — it does not need to be removed for correctness" →
`nightly.py --supervised` calls `load_all_scopes()` with no slug filter and picks
`slug = next(iter(scopes))` — an arbitrary (likely first-inserted) entry, not necessarily
the vetted target, if rejected candidates are left in `programs/`. FIXED: Step 2 now
requires removing rejected candidate scope directories before Step 3 runs.

[CRITICAL] (plan-feasibility-auditor archetype, independently verified) — Task 1 Step 11
(`test_sign_approval_test_mode_gate.py`): only adds `scripts/` to `sys.path`, but
`draft.drafter` internally does fully-qualified `from scripts.draft.errors import ...`
(confirmed in `scripts/draft/drafter.py`), requiring WORKSPACE_ROOT itself on the path —
absent here, unlike sibling nightly tests which get it for free by importing `nightly`
(which self-adds WORKSPACE_ROOT). As written this raises `ModuleNotFoundError: No module
named 'scripts'` before ever reaching `sign_approval.main()`, so Steps 12/14's documented
expected outcomes would not occur. FIXED: added an explicit WORKSPACE_ROOT path insert to
the test file.

[CRITICAL] (risk-rollback, verified via first-principles security reasoning against the
actual threat model) — Task 1 Step 3 (`test_mode_gate.py`): `os.environ.get(
"PYTEST_CURRENT_TEST")` is trivially spoofable by anyone willing to set that variable
before invoking the script directly (`PYTEST_CURRENT_TEST=x python scripts/sign_override.py
--test-mode-confirm ...`) — it defends against accidental/naive misuse but not a deliberate
bypass, which is the actual threat model design §3 exists to close (Task 5 then wires a
real external submission dispatch on top of this same gate). FIXED: added hook-level
enforcement in `hooks/pretooluse.py` (design §3 explicitly allowed this as an "and/or"
option) — unconditionally blocks any Bash-tool-issued command containing
`--test-mode-confirm` targeting sign_approval.py/sign_override.py, no override, layered
alongside the env-var check (which correctly handles the legitimate
subprocess-spawned-from-a-real-pytest-run case the hook can't see into).

[CRITICAL] (scope-cut dimension + plan-scope-cutter archetype + plan-skeptic archetype, 3
independently convergent findings) — Task 3 Steps 8-12 (`authorize_unattended.py` + its
5-test file): nothing in this plan invokes it — Task 4 Step 4 explicitly refrains from
running it — and design §2.3's actual requirement (a freshly-loaded scope stays
supervised-only) is fully satisfied by the schema field + `_filter_unattended_eligible`
alone (Steps 1-7). Design §2.3 never mandates a companion promotion script; its own three
listed mechanism options (unload/flag/TTL) don't call for one either. FIXED: Steps 8-12 cut
entirely; the schema field's description now points at a manual `scope.yaml` edit instead
of the unbuilt script; Task 3's Interfaces/Produces line updated to match.
```

## IMPORTANT

```
[IMPORTANT] (clarity) — Task 4 Step 1: "For each candidate <owner>/<pkg> ... under
consideration" never states where a candidate name comes from. FIXED: added a concrete
starting point (huntr.com's active-bounty listing / GHSA advisory search) as the
candidate-sourcing method.

[IMPORTANT] (clarity) — Task 4 Step 1: only the huntr `fetch_program.py` invocation is
shown, no GHSA equivalent. FIXED: added the `--venue ghsa --identifier GHSA-xxxx-xxxx-xxxx`
example alongside it.

[IMPORTANT] (clarity) — Task 4 Step 2: "whose fixed_version is greater than..." — the real
field in `scripts/recon/advisories.py`'s Advisory record is `fixed`, not `fixed_version`.
FIXED: corrected the field name.

[IMPORTANT] (clarity) — Task 4 Step 1 (vetting loop): no stop/escalation condition; an
executor could iterate indefinitely against failing candidates. FIXED: added an explicit
"after 5 failed candidates, halt and ask the human for direction" stop condition.

[IMPORTANT] (clarity) — Task 4 Step 3: "respond y at each halt ... or omit --yes/pass it if
the session prefers" supplies no decision criterion. FIXED: defaulted to interactive
(respond y at each halt) since the whole point is human supervision of a live run; noted
`--yes` is acceptable only once the operator has already reviewed the target thoroughly in
Steps 1-2.

[IMPORTANT] (clarity, x2 — Task 2 Step 4 and Task 4 Step 5) — "record in the plan's
progress trail (this file, inline...) or the eventual retrospective" is an unresolved
either/or; no "progress trail" section exists anywhere in the plan. FIXED: both now point
at one concrete new "## Execution Log" section appended near the end of the plan file.

[IMPORTANT] (plan-feasibility-auditor archetype, independently verified) — Task 1 Step 11
(`test_sign_approval_test_mode_gate.py`): `draft_findings()` is called with no ledger
isolation, unlike `test_draft_drafter.py`'s autouse `_isolate_ledger` fixture the plan
claims to mirror — every test run would append a real event to the actual, git-tracked
`submissions/ledger.jsonl` (confirmed not gitignored). FIXED: added the same
`_isolate_ledger`-style fixture to the new test.

[IMPORTANT] (completeness) — Task 3: no update to `docs/SCOPE_SCHEMA.md`'s `rules.*` table,
which documents every existing rules field individually and is CLAUDE.md's canonical
scope-normalization doc. FIXED: added a step updating it alongside the schema change.

[IMPORTANT] (completeness) — Task 5: two stale-documentation touchpoints go untouched —
`submit.py`'s own module docstring (still says huntr is "stubbed in Stage 1") and
`docs/SUBMISSION_GATE.md`'s Stage-7-stubbed table (still lists huntr as
"Not implemented until Stage 7"). FIXED: added a step updating both.

[IMPORTANT] (completeness) — `sec-research/CLAUDE.md`'s auto-loaded "Stage 1 vs Stages 2-7"
section states Stage 7 submission integrations are "still pending," which becomes false the
moment Task 5 lands, and no task touches this file. FIXED: added a step in Task 5 updating
this section.

[IMPORTANT] (completeness) — Task 5's new tests exercise only the two pure helper functions
(`_select_dispatcher`/`_status_for_dispatch`); `main()`, `_consume_token` (the actual PT-2
token-validation/consumption logic), `_dispatch_manual_form`, and `_update_finding_status`
remain completely untested even after this plan lands, for a script this workspace's
CLAUDE.md calls load-bearing to one of its 3 invariants. FIXED: added one end-to-end
`main()`-level test exercising token consumption, ledger events, and finding-status update
for the huntr path.

[IMPORTANT] (risk-rollback) — Task 4 has no explicit "Depends on Task 3" callout matching
Task 5's "Depends on Task 1" pattern; without it, worktree/session drift could let Task 4
load a live scope before Task 3's filter is actually committed to the checkout the real
3am cron reads. FIXED: added the explicit dependency header.

[IMPORTANT] (feasibility) — Task 2 Step 1 only preflights Docker, missing a
`claude-cli`-specific check the codebase already has (`ClaudeCliClient.preflight()`) —
risks an uncaught crash instead of a graceful abort on a misconfigured claude-cli. FIXED:
added the claude-cli preflight check alongside the Docker check.

[IMPORTANT] (risk-rollback, x2 — Task 2 and Task 4) — no stated behavior for a
mid-pipeline crash/interruption during either task's real network/Docker/LLM-cost run.
FIXED: added a brief note to each — both are human-supervised, re-runnable-from-the-top
operations; Task 4 additionally already benefits from nightly.py's own journal/checkpoint
design for inspecting how far a prior attempt got.
```

## MINOR (left for the executor's judgment; not blocking)

```
[MINOR] (plan-feasibility-auditor archetype, verified) — Task 1 Step 9: "2 + 4 = 6 passed"
→ tests/hooks/test_override_singleuse.py has 5 test functions, not 4; corrected to
"2 + 5 = 7 passed".

[MINOR] (completeness) — Task 1's new sign_approval.py test lacks the symmetric
"still works under pytest" happy-path test that sign_override.py's version has. FIXED:
added it alongside the existing refusal test for parity.

[MINOR] (completeness) — `submit.py`'s `STAGE_1_FULL = {"manual-form", "ghsa"}` isn't
updated to include "huntr" even though it becomes functionally Stage-1-full. FIXED: added
"huntr" to the set for consistency (in-code documentation, not read at runtime by anything
this plan touches).

[MINOR] (clarity) — Task 3 Step 1 preamble run-on sentence; Verification section's
"git diff --stat across all commits" grammar. FIXED: reworded both.

[MINOR] (risk-rollback) — no bisection guidance if the full suite regresses at Task 5 Step
5, after five tasks' worth of commits have already landed. FIXED: added a one-line note to
the Verification section (bisect via `git bisect` across this plan's own commit range, or
re-run each task's own test file individually per its Step N to isolate).

[MINOR] (plan-skeptic archetype) — Task 5's extraction into two pure helper functions is
more elaborate than a minimal inline 2-line ternary fix; a cheaper variant exists. Not
applied — the extraction is deliberately kept for direct testability (matches this
codebase's existing `score_track_b(..., runner=...)` injection pattern) and is explicitly
called out as a considered tradeoff, not an oversight.
```

## Bottom line

Every CRITICAL and IMPORTANT finding above is fixed in place in the committed plan (no
finding required a fresh re-review — each fix is small, localized, and independently
verifiable against the same source the finding cited). MINOR findings are either applied
(cheap, no tradeoff) or explicitly left as noted judgment calls. The tracker gap (design's
own stated prerequisite) is resolved: `hb-dzz` filed and referenced in both the design and
this plan.
