# Retrospective: Claude-CLI LLM Provider → First Trustworthy sec-research Run (hb-322)

**Plan:** `~/.claude/plans/the-next-highest-value-pure-kettle.md`
**Commit:** `5443bb2` (`docs(sec-research): List all 6 silent-drop event types in ledger check`)
**Date:** 2026-06-30

## Outcome

Added a `claude-cli` LLM provider to sec-research (`scripts/llm/providers/claude_cli.py`) that
authors via the Claude Code CLI's subscription/programmatic-credit-pool billing instead of the
metered Anthropic API, wired into the existing `select_client()` factory alongside `claude` and
`llama`. Used it to drive hb-322 — sec-research's first real supervised pipeline run against a live
huntr.com program (`isaacs/minimatch`) — to a trustworthy, ledger-verified outcome: a defensible
evidence-backed null (no novel finding; ~9 recon-surfaced advisories all targeted transitive
dependencies, not the direct asset, and the model correctly declined to mis-target). hb-322 is
closed; two follow-up beads filed (hb-5i3: per-strategy provider routing to conserve the credit
pool; hb-a2w: harden `nightly.py` against the masked-failure pattern discovered live). 11 commits,
439 tests passing.

## What worked

- **Adversarial plan review before any code.** 9 parallel reviewers (6 dimensions + 3 archetypes)
  on the initial plan caught 11 CRITICAL and 18 IMPORTANT findings before Task 0 ever ran — a
  non-interactive `--yes` gap that would have hung the live run, a Windows `.cmd`-shim subprocess
  bug, a `--until recon` dry-run step whose own success check was unreachable. All fixed in the
  plan text by a dispatched fixer agent before execution. This is the single highest-leverage step
  in the whole delivery: every one of those would have been a live-debugging session otherwise.
- **The Task 1 empirical spike, with a literal gating checkpoint.** Rather than assume the
  `claude -p --output-format json` envelope shape, Task 1 ran the real CLI and found it differs
  materially from the plan's assumption (a JSON array of session events, not a flat object). The
  plan had an explicit "Step 7: Checkpoint — confirm before starting Task 2" instruction; honoring
  it meant Task 2's design was corrected (array-unwrap via `_find_event`, structured
  `rate_limit_event` check) before any implementation code existed, not after a failed test run.
- **Two-tier code review (per-task + final whole-branch) at different scopes.** Per-task reviews
  caught implementation-level issues fast and cheap (stale test counts, a dead import). The final
  whole-branch review, dispatched on the most capable model after all tasks were nominally
  complete, caught something no per-task review could have: a documentation-evidence gap that
  turned out to mask a real, live bug (see below). Scoping the final review wider and to a stronger
  model than the per-task gates paid for itself completely in this one finding.
- **Worktree isolation for live execution.** Running Task 6's real, money-spending pipeline run
  inside an isolated worktree (not on `master` directly) meant the live-discovered bugs and their
  fixes, the rebase, and the multiple re-runs were all reversible until the final merge — nothing
  risked the user's actual branch state mid-debugging.

## Friction / bugs

- **Worktree branched from `origin/master`, 9 commits stale**
  - *What happened:* `EnterWorktree`'s default `baseRef: fresh` branches from `origin/<default-branch>`, not local HEAD. Local `master` was 18 commits ahead of `origin/master` (unpushed). Task 6's first live step (`fetch_program.py`) failed with the exact pre-fix huntr-parser error that an earlier same-day commit (hb-dzu) had already resolved on local `master`.
  - *Root cause:* implicit assumption that "the worktree has today's local work" — never verified before live execution began.
  - *How caught:* the fetch error message literally matched a known-already-fixed bug, prompting a `git log` comparison between the worktree's branch point and local `master`.
  - *Fix:* `git diff --name-only` to confirm no functional overlap in shared touched files, then `git rebase master` (clean, no conflicts since the new provider files didn't intersect the missing commits' touched files).
  - *Rule:* before live-executing any task in a freshly created worktree, diff the worktree's branch point against local `master`/the working branch — don't assume `fresh` baseRef means "current."

- **Non-interactive `_pause_for_inspection` abort (caught pre-execution, not live)**
  - *What happened:* `nightly.py --supervised` calls `input()` at each stage checkpoint; the original plan's dry-run command had no `--yes`, which would EOF-abort immediately under a non-interactive shell tool.
  - *Root cause:* the plan was drafted assuming an interactive terminal; never checked against the actual execution harness's shell semantics.
  - *How caught:* the adversarial plan review's `feasibility` dimension agent, by reading `nightly.py`'s source directly rather than trusting the plan's prose.
  - *Fix:* confirmed `--yes` exists via the actual argparse definition, added it to the plan, reframed inspection as post-hoc journal reading.
  - *Rule:* any plan step that invokes a CLI presumed-interactive (confirmation prompts, pagers) needs its non-interactive flag verified against the harness's actual shell tool before the plan is approved, not discovered live.

- **`_classify_failure` false-positived on the calling session's own metadata**
  - *What happened:* a real failure (`error_max_turns`, from the model invoking a tool instead of answering) was misclassified as "credit pool exhausted" because the failure classifier keyword-searched the FULL stdout blob, which on any non-zero exit still carries the entire system-init event — every tool, MCP server, and plugin name in the *calling* session. An MCP server literally named `"...Intuit Credit Karma"` matched the `"credit"` substring.
  - *Root cause:* the original design assumed stdout-on-failure was small/clean CLI error text; in practice `claude -p`'s stdout always contains the full session-init JSON regardless of exit code, and that JSON is attacker-irrelevant but classifier-relevant noise (it's literally describing *this* session, not the subprocess's own state).
  - *How caught:* direct reproduction with full diagnostic instrumentation (temporarily printing raw stdout/stderr) after the harness's reported error didn't match what manual `claude -p` calls were actually doing.
  - *Fix:* check the structured `rate_limit_event.rate_limit_info.status` first (a real signal), fall back to keyword-matching `stderr` only — never `stdout`.
  - *Rule:* never keyword-match a subprocess's full stdout for status classification when that stdout can echo back orchestration-layer metadata (tool lists, session config) unrelated to the subprocess's actual outcome; prefer a structured signal field over substring search whenever one exists.

- **`--tools ""` doesn't disable MCP-server tools — the masked-failure bug**
  - *What happened:* even after disabling the CLI's *built-in* tool set, `claude -p` still inherited every MCP server connected in the *calling* session (Gmail, Spotify, Drive, ...). The model invoked an inherited MCP tool (Spotify "Search"), hit a transient Cloudflare 502 on the MCP proxy, burned the single allowed turn, and `error_max_turns` fired again — but this time `generate_hypotheses`'s per-item `LLMUnavailable` catch silently absorbed it into what looked exactly like a clean "zero hypotheses" reasoned decision.
  - *Root cause:* `--tools` and MCP server availability are two separate CLI configuration surfaces; disabling one does not disable the other, and nothing in `claude -p --help`'s flag descriptions makes that distinction obvious without testing.
  - *How caught:* **the final whole-branch code review**, which flagged that the outcome note's "trustworthy null" claim wasn't evidenced against the ledger — it could equally describe a masked failure. Investigating that single documentation-rigor flag is what surfaced the actual bug; without it, hb-322 would have closed on a false premise.
  - *Fix:* add `--strict-mcp-config` (with no `--mcp-config`) to drop every inherited MCP server. Re-ran Task 6 twice post-fix; this time the ledger showed zero drop-events, confirming a genuine reasoned `{"hypotheses": []}`.
  - *Rule:* a "clean" terminal state (no exception, no error message) is not evidence of a *correct* outcome when the surrounding code has any silent-catch-and-continue path — always check the actual ledger/audit-log for drop-events with the same shape as a legitimate empty result, not just the absence of a crash. This is the single most important rule from this delivery.

## Concrete improvements

- **`claude_cli.py`'s `build_argv()`** now passes both `--tools ""` and `--strict-mcp-config` — done, landed in commit `a0f5b8b`.
- **`_classify_failure`** now checks structured `rate_limit_event` before any keyword matching, and scopes keyword fallback to `stderr` only — done, landed in commit `5fed247`.
- **hb-5i3** (P3, open) — per-PoC-strategy provider override so the nightly loop spends the credit pool only on PoC-authoring, not hypothesis-gen, conserving the finite monthly allowance.
- **hb-a2w** (P3, open) — `nightly.py` should fail loud (or at least surface visibly) if a supervised run logged any `hypothesis-llm-unavailable`/`hypothesis-parse-error` ledger event, so a fully autonomous run can't silently null on a transient failure the way this delivery's first two live attempts did. This is the generalized fix for the masking pattern discovered above — the `claude-cli`-specific causes are fixed, but the swallow-and-continue architecture in `generate_hypotheses` that let it happen silently is unchanged and pre-existing.
