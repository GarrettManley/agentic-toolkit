# Retrospective: claude-marketplace post-1.0 cycle (WS1 commands-gate + WS3 pre-plan-brief)

**Plan:** `~/.claude/plans/writing-plans-let-s-write-a-encapsulated-mist.md`
**Commit:** `206a468` (`chore(release): retrospective@1.2.0, review@1.3.1`) + `45da141`, `fcca89a`
**Date:** 2026-06-26
**Tracker:** epic `hb-w61` (children `.1`/`.2` closed, `.3` deferred research, `.4` follow-up)

## Outcome

Delivered a tight post-1.0 cycle for the (already-public) claude-marketplace: WS1 extended the frontmatter linter + skill-index generator to cover the 13 `plugins/*/commands/*.md` files (a per-type schema — `description` required, `name` optional but parity-checked) and cut a clean release; WS3 added a `/pre-plan-brief` skill to the retrospective plugin that surfaces matching prior retro findings before planning. Both shipped to `main` (CI green, tri-OS), tagged `retrospective-v1.2.0` + `review-v1.3.1`, GitHub Releases cut. WS2 (privacy guardrail) and WS4 (LLM-mining spike) were cut/deferred by adversarial review before any code was written.

## What worked

- **`/adversarial-review-plan` before execution** — the 9-reviewer pass killed two of four planned workstreams on verified grounds (observations.jsonl is local-only/never-published, so the "privacy guardrail" guarded a non-exposed path; the LLM spike was non-CI-deliverable research). Cutting scope *before* writing code was the highest-leverage moment of the session.
- **Discovery-before-planning** — three Explore agents caught that the marketplace was already public as the full-history dev repo (not the ADR-0007 clean recreation), and that the "build epic" was closed. The original premise ("plan the v1.0 launch") was wrong; the real work was a post-1.0 cycle.
- **TDD + the repo's own pre-commit `verify.sh` gate** — red-first locked the per-type command schema (proving `checkpoint.md`, which omits `name`, must stay valid); 100% line coverage on both changed modules; the commit hook re-ran all 9 gates automatically.
- **WS3 dogfood smoke test** — running `/pre-plan-brief "commands lint"` against the live retro corpus surfaced the exact recurrence ("Repeated the D3 'commands aren't CI-linted' mistake") that the adversarial review had flagged. The tool validated its own reason for existing.
- **Staged-local-then-batch-public** — keeping all commits local until one reviewed public push kept the consumer-facing repo untouched until the work was fully verified.

## Friction / bugs

- **cp1252 console crash in `retro_brief.py`**
  - *What happened:* printing a brief whose retro content contained `→` (U+2192) raised `UnicodeEncodeError` on the default Windows console codepage.
  - *Root cause:* default stdout encoding is cp1252; retro prose carries arrows/checkmarks.
  - *How caught:* the real-corpus smoke test (not the unit tests — capsys captures as UTF-8, so it can't reproduce).
  - *Fix:* `_force_utf8()` reconfigures stdout/stderr to UTF-8 in `main()`.
  - *Rule:* any Windows CLI that prints arbitrary file content must force UTF-8 stdout; this repo had already hit it once (stewardship PR #16). A pure-pytest suite will not catch console-encoding bugs — keep a real-invocation smoke step.

- **CHANGELOG double-H1 leaked into a release note**
  - *What happened:* `release.py` prepends `# <plugin> changelog` above the original hand-authored `# Changelog` intro; the `gh release` note extraction (awk to next `## `) then swallowed the intro prose for retrospective-v1.2.0.
  - *Root cause:* pre-existing repo-wide mismatch (4/5 plugins have two H1s) between release.py's prepend format and the hand-authored intros.
  - *How caught:* eyeballing the generated release notes before/after `gh release create`.
  - *Fix:* `gh release edit` with the correct section by hand; filed `hb-w61.4` to normalize release.py's prepend + the 4 files.
  - *Rule:* always read auto-extracted release notes before publishing; section-extractors assume one H1.

- **All-plugins pytest collection collision** — `pytest ci/tests plugins` errors with "Plugin already registered under a different name" (evidence/git/orchestration). Not a regression; CI runs per-directory to avoid it. *Rule:* verify changed dirs per-directory, never trust an all-at-once run.

## Concrete improvements

- **`ci/lint-frontmatter.py` + `ci/gen-skill-index.py`** — per-type command coverage + a Commands index section — done, shipped (`45da141`, in main).
- **`/pre-plan-brief` skill + command + `retro_brief.py`** (retrospective 1.2.0) — done, shipped (`fcca89a`). 100% coverage.
- **`hb-w61.4`** — normalize per-plugin CHANGELOG double-H1 / release.py prepend — filed, open.
- **`hb-w61.3`** — LLM-tier instinct mining (deferred research, local-GPU-only, non-CI) — filed, open, deliberately out of cycle.
- **Meta:** WS1's lint found the 13 command files already clean — the gate was *preventative*, not a defect-catch; the load-bearing value of WS1 was the release cut + future drift protection, exactly as the plan's own watch-point predicted.
