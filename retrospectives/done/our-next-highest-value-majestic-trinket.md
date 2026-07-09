# Retrospective: Kill the Workspace hook-router spawn amplifier (matcher-scoping)

**Plan:** `~/.claude/plans/our-next-highest-value-majestic-trinket.md`
**Commit:** `41c0cd2` (`fix(hooks): scope router matcher to side-effecting tools (hb-0nh)`)
**Date:** 2026-07-08

## Outcome

Narrowed the Workspace-root hook federation router's `PreToolUse`/`PostToolUse` matchers in
`.claude/settings.json` from a broad `.*` to an anchored side-effecting-tools allowlist
(`^(Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit|WebFetch)$`) plus the three sec-research-gated
`mcp__` network-tool families (chrome-devtools-mcp, playwright, firecrawl). Read-only/orchestration
tools (`Read`/`Grep`/`Glob`/`Task`/…) no longer spawn `hook_router.py` at all — eliminating the ~4-spawn
+ full-tree-walk cost per tool call that was amplifying into session stalls under subagent fan-out.
Closes `hb-0nh`. A regression test asserts the live `settings.json` matcher against the router's own
`matcher_matches()` for both the excluded and included tool sets.

## What worked

- **Reading source before diagnosing.** The task originated as a *selection* problem ("pick the next
  highest-value aether-engine work") but pivoted mid-session when parallel Explore agents reproducibly
  stalled — a live repro of a bug already diagnosed in a prior session's memory. Reading `hook_router.py`
  / `hook_router_lib.py` / the design doc directly (not trusting the memory's or bead's framing) found
  the actual root cause and immediately falsified part of the bead's own framing: hb-0nh asked for an
  "in-router fast-path," but the router process is already running by the time any in-router code
  executes — only the `settings.json` matcher (evaluated by Claude Code *before* spawning) can actually
  skip the spawn. The design doc itself pre-blessed this exact fix in its Risks section.
- **AskUserQuestion for scope, not for permission-seeking.** Three genuine judgment calls (deliverable
  vs. quick unblock, matcher-scoping vs. in-router vs. cache, minimal vs. scoped-up) were surfaced as
  structured choices with previews rather than narrated as open questions — kept the session moving
  without guessing at scope the user cared about.
- **TDD red-then-green, twice.** Task 1's test failed against the pre-fix `.*` matcher as expected. Then
  step-10 adversarial review proved the *first* "fix" was itself still wrong (see below) — writing the
  assertion as data-driven tool-name lists (`READ_ONLY_TOOLS`/`SIDE_EFFECTING_TOOLS`) made it cheap to
  extend and re-verify rather than rewriting test logic.
- **Adversarial code review caught a real correctness bug the plan-writer (me) missed.** Two
  `pr-review-toolkit` agents (`code-reviewer`, `silent-failure-hunter`) ran in parallel on the landed
  diff. Both flagged the same root defect from different angles — an unanchored regex under `re.search`
  substring semantics — which is exactly the kind of thing a solo pass tends to rationalize past ("it's
  fine, low-frequency" — which I had literally written into the plan and was wrong about).
- **Verifying reviewer findings against source rather than applying them blindly.** One CRITICAL finding
  (WebSearch as a PT-1 scope-check gap) was disproven by reading `sec-research/hooks/pretooluse.py:100-102`
  directly — PT-1 explicitly exempts WebSearch. Applying it would have been unnecessary scope creep with
  a wrong justification. The companion mcp__-tools half of the same finding *was* real and got fixed.

## Friction / bugs

- **Bare `python` resolves to the WindowsApps app-execution-alias stub in Git Bash on this machine.**
  - *What happened:* `python -m pytest ...` failed with `Permission denied` (exit 126); a git pre-commit
    hook using `PYTHON="${PYTHON:-python}"` hung for >2 minutes on the same stub instead of failing fast
    (inconsistent behavior depending on invocation context — direct argv[0] vs. piped into `python -c`).
  - *Root cause:* `where python` resolves `C:\Users\Garre\AppData\Local\Microsoft\WindowsApps\python.exe`
    (the Store app-execution-alias) ahead of the real interpreter
    (`C:\Users\Garre\AppData\Local\Python\bin\python.exe`) on Git Bash's `PATH`.
  - *How caught:* first pytest invocation failed immediately with a clear `Permission denied`; the git
    hook manifestation was a silent hang requiring process/lock-file inspection to rule out a genuine
    stuck commit before retrying with `PYTHON=` set explicitly.
  - *Fix:* used the real interpreter path directly for pytest; set `PYTHON=<real-path>` env var for the
    git hook invocation (the hook already supported this override).
  - *Rule:* on this machine, never invoke bare `python` from Git Bash for anything that must actually
    run — resolve `C:/Users/Garre/AppData/Local/Python/bin/python.exe` explicitly, or set `PYTHON=`
    for any script/hook that reads that env var. Worth fixing at the PATH level as a follow-up so this
    stops recurring per-session.
- **Unanchored regex + `re.search` substring semantics defeated the fix's own purpose.**
  - *What happened:* the first matcher (`Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit|WebFetch`,
    unanchored, matching the existing verify-gate hook's style) still matched `TodoWrite` (contains
    `Write`) and `BashOutput` (contains `Bash`) — two very-frequently-called tools in exactly the
    subagent-heavy workflows the fix targeted.
  - *Root cause:* `matcher_matches()` uses `re.search`, not `re.fullmatch`; the plan explicitly considered
    this exact substring-collision risk during planning and dismissed it as "low-frequency, fine" —
    a wrong empirical assumption made without checking actual tool-call frequency.
  - *How caught:* adversarial code review (both dispatched agents independently), not by me during
    planning or execution — the regression test I wrote didn't include `TodoWrite`/`BashOutput` in its
    exclusion list, so it passed despite the leak.
  - *Fix:* anchored the short-tool-name group as `^(...)$`; added `TodoWrite`/`BashOutput` to the test's
    `READ_ONLY_TOOLS` list so the boundary is now pinned.
  - *Rule:* when scoping a regex matcher against an unanchored `re.search` engine, enumerate the
    *frequent* tool names in the exclusion set as literal test cases before shipping — "low-frequency"
    is a claim that needs checking, not asserting. This generalizes beyond hook matchers to any
    substring-based allow/deny list.
- **A pre-existing, unrelated `pre_commit_audit.ps1` gate failure blocked the commit.**
  - *What happened:* 16 "Hardcoded TBD" failures in marketplace/skill files (`architect.agent.md`,
    `compliance.agent.md`, `README.md`, `SKILL.md`, `completeness.md`) — none touched by this diff.
  - *Root cause:* the audit scans repo-wide, not just staged/diff files; those TBDs predate this session.
  - *How caught:* ran the mandated pre-commit verify scripts before proposing a commit, per the
    Workspace verify-gate discipline.
  - *Fix:* used the documented, auditable `[verify-override: <reason>]` commit-message mechanism after
    confirming via `git status`/`git ls-files` that zero overlap existed between the failing files and
    the staged diff — with explicit user authorization via AskUserQuestion rather than a unilateral call.
  - *Rule:* a hard-block gate failing on files outside the current diff is a legitimate override
    candidate, but the override choice belongs to the user, not to the agent silently applying it,
    even when the override is well-justified.

## Concrete improvements

- **hb-0nh** — closed, landed in commit `41c0cd2` (Workspace repo).
- **PATH fix for `python`** — not done this session; worth a follow-up so bare `python` resolves
  correctly in Git Bash without per-command workarounds. No bead filed yet.
- **16 pre-existing `pre_commit_audit.ps1` TBD failures** — not filed as a tracked item this session
  (out of scope for hb-0nh); flagged here so a future session doesn't rediscover them from scratch.
- **hb-ry9 (discovery cache)** — remains open/deferred; explicitly out of scope, value further reduced
  now that read-only tools skip the router entirely.
