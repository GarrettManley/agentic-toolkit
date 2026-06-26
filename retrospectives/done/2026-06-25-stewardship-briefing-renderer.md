# Retrospective: Stewardship Morning-Briefing Renderer (D5)

**Plan:** `~/.claude/plans/2026-06-25-stewardship-briefing-renderer.md`
**Commit:** `513b263` (`feat(stewardship): morning-briefing renderer (D5, #8) (#15)`)
**Date:** 2026-06-25

## Outcome

Shipped `stewardship@1.3.0`, fulfilling the template's long-standing "wire your own renderer" promise. `render_briefing.py` subprocess-invokes the three steward source scripts with `--json`, derives a status line + rule-based suggested actions, and substitutes the six `{{TOKEN}}` placeholders in `templates/morning-briefing.md`. `auto_memory_housekeep.py` gained a `--json` flag (the one source lacking one). Delivered both as the `/morning-briefing` command (the plugin's first) and a 4th nightly steward step across all three platform schedulers. 16 new tests, 100% coverage on both scripts; PR #15 squash-merged; `stewardship-v1.3.0` reconciled to the squash commit. **This was the final feature wave — D1–D5 of epic `hb-28u` are all shipped.**

## What worked

- **Pure/subprocess split for testability.** Separating the deterministic render/derive functions from the subprocess collection meant 12 of 16 tests are pure (synthetic dicts, no subprocess), and the integration tests cover the boundary. 100% coverage fell out naturally, no subprocess mocking.
- **Adversarial review, fourth wave running.** Nine agents again caught real plan errors before execution (see Friction). The `docs:plan-feasibility-auditor` did the heaviest lifting — it traced `drift_check`'s exit-code path to *confirm* the `run_json` logic was safe, turning a suspected CRITICAL into a verified non-issue rather than a wild-goose fix.
- **`--date`/`--json` injection seams.** Deterministic clock + structured output made the renderer fully testable headless; the same `--json` seams are what the renderer consumes in production.
- **The dev-clone pre-commit `verify.sh` gate caught the ruff E702** (semicolon) the instant I committed — fix-and-recommit took one cycle, no CI round-trip.
- **Inline tag reconciliation, now reflexive.** Re-pointing `stewardship-v1.3.0` to the squash commit immediately post-merge; `release.py --dry-run` clean. Fourth wave in a row.

## Friction / bugs

- **`coverage report` was inert (no data)**
  - *What happened:* The plan's coverage steps ran `coverage report --include=… --fail-under=90` with no preceding `coverage run`.
  - *Root cause:* `pytest.ini` has no `--cov` addopt and `.coveragerc` is data-driven, so a bare `coverage report` errors "No data to report." I'd carried the pattern loosely from D4 (where I *did* run `coverage run` first in execution, but wrote the D5 plan sloppily).
  - *How caught:* `docs:plan-feasibility-auditor`, against `pytest.ini`.
  - *Fix:* Every coverage step is now `coverage run -m pytest <tests> && coverage report --include=… --fail-under=90`.
  - *Rule:* A `coverage report` line in a plan is only valid if a `coverage run` precedes it in the same step — check `pytest.ini` for `--cov` before assuming pytest produces coverage data.

- **Repeated the D3 "commands aren't CI-linted" mistake**
  - *What happened:* The plan claimed the new `/morning-briefing` command would be validated by `validate-plugins.py` (auto-discovered).
  - *Root cause:* `validate-plugins.py` checks only `plugin.json`; `lint-frontmatter`/`gen-skill-index` glob only `skills/SKILL.md` + `agents/*.md`. No gate touches `commands/*.md`. This is the **exact** finding from the D3 retro — I wrote it down and still repeated it one wave later.
  - *How caught:* completeness + feasibility-auditor agents.
  - *Fix:* Plan now states the command is auto-discovered at runtime but has no CI frontmatter gate (manual self-check).
  - *Rule (now twice-confirmed, escalate):* New `commands/*.md` are unvalidated by CI — never claim a gate covers them. **A retro finding is not a fix; it only helps if I re-read retros before planning the next similar wave.** Consider a `commands/` lint as real backlog, not just a note.

- **Over-built error handling against the user's own preference**
  - *What happened:* The plan threaded a `{"error"}` sentinel + `if "error" in …` branch through all six render functions plus an `UNAVAILABLE` status.
  - *Root cause:* Reflexive defensive coding for in-repo, contract-guaranteed sources that can't realistically fail mid-render — directly contradicting AGENTS.md ("don't add error handling for scenarios that can't happen; trust internal code").
  - *How caught:* `docs:plan-scope-cutter` (+ value/skeptic), explicitly citing the AGENTS.md rule.
  - *Fix:* Collapsed to one boundary catch in `run_json` + centralized degradation in `build_sections`; render functions assume valid data; dropped three speculative tests.
  - *Rule:* Subprocess boundaries warrant *one* catch; everything downstream of a contract-guaranteed in-repo source should trust the data. Re-read the "no can't-happen error handling" rule when a plan grows per-function error branches.

- **Template prose leaked a literal `{{TOKEN}}` into every render**
  - *What happened:* `test_main_writes_briefing` failed its `"{{" not in text` assertion — the template's intro paragraph literally contained `` `{{TOKEN}}` `` as documentation, which survived substitution.
  - *Root cause:* The skeleton's intro was written for template-*readers*; once a renderer fills it, that prose ships in every briefing.
  - *How caught:* the integration test's no-leftover-token assertion (TDD red caught it immediately).
  - *Fix:* Rewrote the intro to a rendered-briefing-appropriate line (Task 5.5, pulled forward).
  - *Rule:* A template's own documentation prose is output once a renderer exists — strip meta-instructions from templates that get rendered verbatim.

- **Plan-mode marker keyed to the stale umbrella path (now four waves running)**
  - *What happened:* Same as D3/D4 — ExitPlanMode echoed the old umbrella plan; no pending marker for the dated D5 slug.
  - *Rule (stable pattern):* Each wave: write the plan to a fresh dated path, drive `/plan-completion` + `/plan-retrospective` by explicit path. Confirmed across D3–D5.

## Concrete improvements

- **ADR-0011** records why subprocess over import (each script owns its `--json` contract; renderer is a thin composer), the 03:00 idempotent double-run, and the `-ApplyHousekeep` ordering. Pre-empts the obvious "why not just import?" question the skeptic raised. Done.
- **`auto_memory_housekeep --json`** gives the memory pass a structured contract reusable beyond the briefing. Done.
- **D5 closes the program** — the four nightly steward steps (drift / housekeep / horizon / briefing) now compose into one rendered morning view. Done.
- **Recurring squash-orphan toil → D6 (#11).** Reconciled the release tag by hand for the *fourth* consecutive wave (D2–D5). This is now clearly worth automating; #11 is filed and should be the next wave if the program continues. Follow-up.
- **Meta:** two retro findings (commands-not-linted, plan-mode marker) recurred from earlier waves. The lesson isn't the finding — it's that **retros only pay off if read before the next similar plan**. Worth a pre-planning habit: skim recent retros for the plugin/area being planned. Process follow-up.
