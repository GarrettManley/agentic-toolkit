# Retrospective: hb-a2w — Surface Hypothesize-Stage LLM Failures Loudly (Both Entry Points)

**Plan:** `sec-research/docs/superpowers/plans/2026-06-30-hb-a2w-nightly-fail-loud-ledger.md`
**Commit:** `b8de789` (`feat(sec-research): nightly.py --supervised surfaces hypothesize failures live at the checkpoint (hb-a2w)`), final of 3 (`5b809dc`, `f934da8`, `b8de789`)
**Date:** 2026-06-30

## Outcome

Closed the last open masking-pattern gap from hb-322's first live run: `generate_hypotheses` has two transient-failure ledger event types (`hypothesis-llm-unavailable`, `hypothesis-parse-error`) that previously produced the exact same silent "zero hypotheses" shape as four legitimate reasoned drops. Shipped a two-layer fix — `stage_briefing()` (shared by both pipeline entry points) now flags any such failure in the human-readable morning briefing, and `run_supervised`'s hypothesize checkpoint additionally prints a live stderr warning and a distinct journal outcome. 3 tasks, 3 commits, 447 tests passing (439 → 447, all new, no regressions). Pushed to `origin/master`.

## What worked

- **Adversarial plan review before any code, again.** The 9-reviewer pass (6 dimensions + 3 archetypes) caught two CRITICAL defects in the original plan before Task 1 was ever dispatched: the plan only protected the rarely-used manual `--supervised` mode, missing the path that actually runs unattended every night; and the field the design used to identify "which item failed" (`slug`) wasn't actually a per-item identifier. Both findings were corroborated by 3+ independent reviewers each before I trusted them.
- **Verifying a corroborated claim directly before acting on it.** Three reviewers flagged the cron-path gap from static analysis; I confirmed it was live, not theoretical, with `Get-ScheduledTask` (`sec-research-nightly`, state `Ready`) before redesigning around it. That one command turned "a reviewer thinks this matters" into "this is currently running in production unprotected" — a materially different planning input.
- **SDD per-task review loop with zero fix waves.** All three tasks passed their task-scoped review clean on the first pass — each reviewer independently re-verified claims against the live file (not just the diff) for things like call-site counts and event-type vocabulary, and found nothing the implementer's report didn't already state accurately. The brief/report file-handoff pattern (`task-brief` → implementer writes to `task-N-report.md` → reviewer reads brief + report + diff package) kept controller context clean across 3 implementer + 3 reviewer + 1 final-reviewer dispatch.
- **One shared `ledger_count_before_run` variable, not two.** Task 2 introduced the snapshot; Task 3 was explicitly instructed to reuse it rather than add a second counter. The final whole-branch reviewer specifically verified there was no duplication — a small DRY decision made up front saved a review finding later.

## Friction / bugs

- **The plan's original scope missed the actual production entry point**
  - *What happened:* The plan (and the bead it came from) was titled "if a supervised run logged..." and only wired the fix into `run_supervised`. `run_unattended` — invoked by `run_nightly.ps1` with zero flags, the function `main()` dispatches to by default, and the function the registered `sec-research-nightly` Scheduled Task actually runs nightly — has the identical swallow-and-continue call and got nothing.
  - *Root cause:* The bead's own narrative ("a fully autonomous nightly.py run with nobody reading the ledger would silently null") describes the cron path far better than the manually-invoked supervised path it was scoped to, but nobody re-checked which code path that narrative actually pointed at before writing the plan.
  - *How caught:* plan-skeptic and completeness dimension agents independently, both citing `run_nightly.ps1`'s exact invocation; confirmed live via `Get-ScheduledTask`.
  - *Fix:* Redesigned around the shared `stage_briefing()` function both entry points already call, rather than only extending the supervised-only journal mechanism.
  - *Rule:* When a bead's stated risk is "an unattended/autonomous run could silently fail," verify which actual code path is the one invoked with zero human present (grep the scheduler/cron wrapper script) before assuming the manually-invoked mode is the one that needs the fix.

- **A kwarg name implied per-item identity it didn't have**
  - *What happened:* The original design used `slug` (passed to every `hypothesis-*` ledger event) as "the recon item identifier" in the warning text. `slug` is actually the program-level scope slug, set once per program and constant across every recon item/asset in a run — the real per-item identifier (`asset`) was captured by the ledger event but never read.
  - *Root cause:* Assumed a field present on every relevant event was therefore a unique-enough identifier, without checking the producer code's actual variable scope (`recon_item.py`'s `build_recon_item(slug, asset, ...)` shows `slug` is an outer-loop constant).
  - *How caught:* clarity dimension agent, independently re-verified by me against `recon_item.py:51` before accepting the finding.
  - *Fix:* `_failure_identifier(event)` helper added, preferring `event["asset"]` and falling back to `event["slug"]` only for the one event type (`hypothesis-parse-error`) that doesn't capture `asset`.
  - *Rule:* A field name suggesting identity ("slug") is a hypothesis, not a fact — check the producer's actual variable scope before using it as a unique key in operator-facing output.

## Concrete improvements

- **hb-a2w** — closed.
- **`investigate.py`'s dead `stage_draft_findings` call** — discovered as a side effect of the final review's backward-compatibility check (it's `stage_briefing`'s only other caller, and predates this change). `stage_draft_findings(verified)` doesn't match that function's actual `(novel, slug, *, today)` signature — the script was already broken before this work, unrelated to hb-a2w. Filed as `hb-n1j` (P3, harness backlog) rather than silently left for the next person to trip over.
- **3 Minor findings from the final whole-branch review** — left unfixed, all forward-looking hygiene on the now-dead `investigate.py` call site (a `# NOTE:` about the `ledger_count_before_run=0` default's "scan everything" semantics) and test-coverage breadth (no test combining a transient failure with a reasoned drop in the same run). Recorded in `.superpowers/sdd/progress.md`'s final-review entry for whoever next touches this area.
