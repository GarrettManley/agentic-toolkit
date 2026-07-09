# Retrospective: hb-168 — Cap oversized tool_input at capture

**Plan:** `claude-marketplace/docs/superpowers/plans/2026-07-09-hb-168-tool-input-cap-plan.md`
**Commit:** `94a5352` (`fix(learning): collapse tool_input nesting past _MAX_DEPTH (hb-168)`) — final code commit on branch `fix/hb-168-tool-input-cap` (4 commits); PR pending user authorization.
**Date:** 2026-07-09

## Outcome

Delivered hb-168 through the full `/deliver` lifecycle. `plugins/learning/scripts/observe.py` now head-caps oversized `tool_input` string values at capture — mirroring the existing `cap_tool_response` — so Write/Edit file bodies can't re-bloat `observations.jsonl` (the vector that grew it to 75.5 MB and taxed every hook append via Defender rescans). Single-task change: `observe.py` + `test_observe.py` (8 new tests) + `README.md`. The delivery started as a two-task plan and was cut to one by adversarial review. Landed on branch `fix/hb-168-tool-input-cap` in claude-marketplace; push + PR await authorization.

## What worked

- **Escalating the plan review to FULL because Phase 0 was skipped.** The auto-triage would have run SCALED (feasibility only), which *drops* `plan-skeptic` and `plan-scope-cutter` on the assumption Phase 0 already vetted premise/scope. Since Phase 0 was skipped (not approved), those were exactly the missing lenses — and the scope-cutter cut an entire second task (nightly re-cap) as YAGNI, while risk-rollback caught a RecursionError crash path, all before any code existed.
- **Deriving the design from real consumers, not the bead's prose.** Grepping `analyze.py` for actual `tool_input` reads (`command`, `file_path`, `edits[].file_path`) is what made the "head-cap every string, no preserve-set special-casing" simplification provably safe.
- **Two distinct review gates each caught a distinct real defect.** Plan review cut a task + flagged recursion; the whole-branch code review (full capability) then caught what the plan review missed — the depth guard returning deep subtrees verbatim.
- **Inline execution for one small task in the nested clone.** Sidestepped the documented PR #26 wrong-checkout hazard that motivates the deliver skill's own cwd-confirmation guard.

## Friction / bugs

- **Depth guard was a half-measure the plan review didn't catch**
  - *What happened:* `cap_tool_input`'s `_MAX_DEPTH` gate prevented the function's own RecursionError but returned deep subtrees *verbatim* — leaving strings nested past depth 40 uncapped and the docstring overclaiming "the hook can't crash."
  - *Root cause:* the plan review reasoned about the function's contract, not the full hook path (`main()` also does `json.loads(stdin)` and `json.dumps(obs)`, both recursive).
  - *How caught:* whole-branch code review — `code-reviewer` and `silent-failure-hunter` converged independently.
  - *Fix:* collapse containers past `_MAX_DEPTH` to a short marker (bounds size *and* flattens nesting so `json.dumps(obs)` is safe), honest docstring, +1 test. Commit `94a5352`.
  - *Rule:* a recursion-safety guard must be traced through the **whole caller path** (parse + serialize), not just the guarded function; the residual pre-existing `json.loads`-on-stdin crash is filed as **hb-vyv**.
- **Windows coverage `--include` glob returned "No data"**
  - *Root cause:* coverage stores Windows paths with backslashes; the plan's `--include='*plugins/learning*'` (forward slashes) matched nothing.
  - *How caught:* the verification command produced "No data to report."
  - *Fix:* used `--source=plugins/learning/scripts` instead.
  - *Rule:* on Windows, prefer `coverage --source=<dir>` over `--include='*a/b*'` globs.
- **Combined coverage floor unrunnable locally**
  - *Root cause:* pre-existing env-specific failures in other plugins (discipline fails 4 git-state/fs tests even without coverage) in this Windows env — unrelated to a learning-only change.
  - *How caught:* diagnosed by running discipline's suite without coverage.
  - *Fix:* honest-gate — delegated the floor to CI (authoritative on the PR), documented the coverage-additive argument; did not overclaim a local pass.
  - *Rule:* a coverage-additive single-plugin change can't regress the combined floor — delegate it to CI rather than fight local env failures.

## Concrete improvements

- **hb-vyv (P4)** — filed: pre-existing `json.loads`/`json.dumps` RecursionError on adversarial deeply-nested `tool_input` in `observe.main()`; broaden the parse guard. Follow-up, out of hb-168 scope.
- **Land pending** — branch `fix/hb-168-tool-input-cap` (4 commits) awaits authorization to push + open the PR (`land-policy: pr`). **hb-168 stays open until the PR merges.**
