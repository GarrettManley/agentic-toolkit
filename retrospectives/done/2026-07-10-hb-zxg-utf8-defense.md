# Retrospective: hb-zxg — systemic UTF-8 defense in run_with_flags

**Plan:** `~/.claude/plans/our-next-highest-value-drifting-simon.md` (+ `.review.md`)
**Branch:** `fix/hb-rap-hook-error-observability` (hb-rap 10 commits + hb-zxg 3 commits + 1 chore(release)); PR pending user authorization.
**Release:** discipline 1.2.1 / learning 1.6.1 / stewardship 1.4.2 (`release.py --apply` committed; `--tag` on main after squash-merge per ADR-0012).
**Date:** 2026-07-10 · Closes hb-zxg (on merge). hb-rap also ships in this PR (was already delivered, awaiting land).

## Outcome

Delivered hb-zxg (ADR-0014 D1): `run_with_flags` now reconfigures stdin/stdout/stderr to UTF-8 as the first act of `main()`, so a wrapped hook writing non-ASCII to stdout (the surface.py `->` class) can't crash on a strict cp1252 console — previously that crash was swallowed and the hook silently never ran. The delivery **pivoted** mid-flight: the work-target was "hb-rap + hb-zxg," but the adversarial plan review discovered hb-rap was already implemented, reviewed, and retro'd on an unmerged branch (awaiting PR authorization). So the real work became: adopt + land the existing hb-rap branch, and stack hb-zxg (the genuinely-undone half) on top — one combined PR, one 3-plugin release.

## What worked

- **The FULL adversarial plan review earned its cost twice over — again.** Its feasibility-auditor found that hb-rap was *already done* on an unmerged branch (10 commits, its own code review + retro), which my three plan-mode Explore agents had missed because they surveyed beads/current-state but never enumerated unmerged branches. Re-implementing would have duplicated reviewed work. It *also* falsified the plan's regression-test premise (see below).
- **Empirical reproduce-before-trust (hb-lv9 discipline) killed a false-universal test.** The plan's hb-zxg regression targeted **stderr**, but a 2-line probe proved `sys.stderr` uses `backslashreplace` (never raises); the crash class is **stdout** (strict cp1252). The test was rewritten to assert arrow-in-stdout (absent pre-fix, present post-fix) — a genuinely discriminating signal.
- **The whole-branch code review (full capability, not down-routed) caught a real, verified CRITICAL.** `reconfigure(encoding="utf-8")` silently resets the error handler to `strict`, stripping stderr's `backslashreplace` — so a lone-surrogate hook-error message would crash the swallow-site print and *break the hook chain*, the opposite of fail-open. Both reviewers reproduced it live. Fixed with `errors=stream.errors`; a mechanism probe confirmed it. It also found the shell/generic spawn paths decode child output with the cp1252 locale (a pre-existing unlogged crash), fixed with `encoding="utf-8", errors="replace"`.
- **Following the bug downstream found a latent briefing crash.** A surrogate in a hook-error message → written to the sink → `render_briefing`'s strict-UTF-8 `write_text` crashes → the user gets *no* briefing, defeating hb-rap's entire purpose. Fixed at the source (`_append_hook_error` sanitizes via `backslashreplace`) so the wrapper never emits crash-inducing content — making "systemic UTF-8 defense" honest end-to-end.
- **Stash-based pristine comparison settled every flake question.** Repeatedly stashing my edits and re-running proved each suspicious failure (discipline snapshot, stewardship render_briefing) was pre-existing, not mine.

## Friction / bugs

- **Test pollution of the real sink — the hb-rap retro's CRITICAL scar, re-triggered.**
  - *What happened:* early runs left `arrow_hook.py`/`surrogate_hook.py` records in the developer's real `%LOCALAPPDATA%\...\hooks-errors.jsonl`; the stewardship briefing tests (which read the real sink) then crashed on the surrogate content.
  - *Root cause:* hb-rap added `read_hook_errors` to `render_briefing.main()` but its stewardship briefing tests never isolated `LEARNING_DATA_ROOT` — they pass only when the real sink is clean.
  - *Fix:* an autouse `LEARNING_DATA_ROOT` isolation fixture in stewardship's conftest + explicit isolation on the cp1252 subprocess test; cleaned the polluted real sink.
  - *Rule:* when a shared/vendored function gains a filesystem side-effect, audit **every** consuming suite for isolation — including the *reader* plugin's tests, not just the writer's.
- **Repo-wide test contamination amplified by methodology.** discipline (snapshot/frontmatter), stewardship (render_briefing), and ci/tests (`OSError`) all flake nondeterministically under rapid sequential single-process runs + repeated `git stash`. Proven pre-existing (fails on pristine; passes in isolation; hb-rap shipped through windows-latest CI). CI runs per-dir in fresh processes and is unaffected.
  - *Rule:* on this repo, trust `verify.sh` + per-*file* isolation runs + fresh-process CI over a full-suite single-process local run; a wandering full-suite failure is contamination until proven otherwise (stash + isolate).
- **Plan-mode Explore agents don't enumerate unmerged branches.** The value-probe survey checked beads and current state but missed a completed-but-unlanded branch.
  - *Rule:* when scoping "next work," `git branch --list` for in-flight branches matching the bead id before planning a from-scratch implementation.

## Concrete improvements / follow-ups

- **PR pending** — push `fix/hb-rap-hook-error-observability` + open the PR (land-policy: pr); `release.py --dry-run` confirms the 3 bumps. hb-rap + hb-zxg both close on merge; run `release.py --tag` on main immediately after the squash.
- **Pre-existing repo test-contamination** (discipline snapshot / stewardship render_briefing / ci `OSError`) is real quality debt but CI-invisible and out of scope here — already noted in the hb-rap retro / memory; not re-filing a duplicate tracker.
- **hb-w61.8** (retrofit the now-hardened wrapper onto the 5 ungated hook plugins) is the natural next step; weigh it against Python 3.15's default UTF-8 mode (PEP 686), which retires this crash class on interpreter upgrade.
