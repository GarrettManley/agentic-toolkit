# hb-322: First Real Supervised Run — Outcome (2026-06-30)

**Tracker:** hb-322 (P1, sec-research's first real end-to-end run vs huntr.com, supervised, trustworthy outcome).

## Terminal outcome

**(c) Defensible evidence-backed null**, full hypothesis audit trail, journal at
`runtime/journals/2026-06-30-huntr-isaacs-minimatch.md`:

```
Checkpoint — recon:       reached, 2 recon items
Checkpoint — hypothesize: reached, hypotheses generated: 0
Checkpoint — verify:      reached, verdicts: 0 (0 verified)
Checkpoint — triage:      reached, novel after dedup: 0
Checkpoint — draft:       reached, findings drafted: 0 (none)
Result: NULL result — no novel confirmed finding; see verdicts for the audit trail
```

## Why the null is trustworthy, not a gap

Recon resolved `minimatch@10.2.5` and surfaced 9 `known_advisories` from the lockfile scan
— but every one of them targets a **transitive** dependency (`brace-expansion`, `tar`,
`uuid`, `ws` ×2, `markdown-it`, `linkify-it`, `ip-address`, `@sigstore/core`), none targets
`minimatch` itself. The single eligible playbook
(`dependency-cve/known-advisory-confirmation`) explicitly scopes v1 to the **direct**
asset (negative signal: "The advisory targets a different package than the asset
(transitive-only; v1 targets the direct asset)"). The model — running through the new
`claude-cli` provider — correctly declined to mis-target a transitive advisory onto
`minimatch`, producing zero hypotheses rather than a fabricated finding. This is the
evidence-grounded behavior `sec-research/CLAUDE.md` requires, confirmed working under a
real external target rather than a fixture.

## Provider validation: what this run did and did not exercise

- **Confirmed live:** `select_client("claude-cli")` → `ClaudeCliClient.complete_json()`
  was called for real, against `claude -p --output-format json`, with `ANTHROPIC_API_KEY`
  absent (subscription/credit-pool path), at the hypothesize stage
  (`llm/generate.py::generate_hypotheses`). The env bridge (`SECRESEARCH_LLM_PROVIDER`,
  `SECRESEARCH_POC_STRATEGY` set before `nightly.py --supervised` in one continuous
  shell session) worked correctly.
- **NOT exercised:** the verify stage's PoC-authoring call (`LLMPocStrategy.build_plan`
  → `complete_json` against `POC_AUTHOR_SCHEMA`) — the original motivating reason
  hb-322 needed Claude in the first place (hb-26v: local 7B PoC authoring is non-viable).
  With 0 hypotheses, there was nothing to verify, so the differential-oracle/PoC-authoring
  path through `claude-cli` was never invoked. **The deeper question — does `claude-cli`
  reliably author discriminating PoCs — remains untested by this run.** This is a real,
  residual gap, not a closed question; the next real run against a program with a genuine
  direct-asset known-CVE (or the next iteration of this one, once huntr surfaces a real
  minimatch CVE) is the actual validation point for that path.

## Two live-discovered bugs, fixed mid-run (commit `5fed247`)

The first two real attempts failed with `LLMConfigError: programmatic credit pool appears
exhausted or rate-limited` — investigated and found to be a **false positive**, not real
pool exhaustion (`claude -p` direct calls succeeded fine throughout, `rate_limit_info.status`
was `"allowed"` every time it was checked):

1. **Tool-use turn exhaustion.** Without `--tools ""`, the model invoked `ToolSearch`
   instead of answering directly with JSON, against the real (larger, production)
   hypothesis-generation prompt — burning the single allowed turn (`--max-turns 1`) with
   no final text result, exiting non-zero with `subtype: "error_max_turns"`. Fixed by
   adding `--tools ""` to `build_argv()` — this adapter is a pure JSON-completion call
   with no legitimate use for tool access.
2. **Unsound failure classification.** `_classify_failure` keyword-searched the *entire*
   stdout blob (which on any non-zero exit still carries the full session-init event —
   every tool, MCP server, and plugin name in the *calling* session). An MCP server
   literally named `"...Intuit Credit Karma"` matched the `"credit"` keyword, misclassifying
   the unrelated `error_max_turns` failure as pool-exhaustion. Fixed: check the structured
   `rate_limit_event.rate_limit_info.status` first (the reliable signal Task 1's spike
   surfaced), fall back to keyword-matching `stderr` only — never `stdout`.

Both fixes are covered by new regression tests (`test_cli_build_argv_disables_tools`,
`test_cli_complete_json_pool_exhausted_via_structured_rate_limit_event`,
`test_cli_complete_json_does_not_misclassify_session_metadata_as_pool_exhaustion`). Full
suite: 438 passed, 6 skipped, post-fix.

## Worktree base-staleness (unrelated but blocking, fixed mid-run)

The execution worktree branched from `origin/master` (9 commits behind local `master`),
missing the hb-dzu huntr-fetcher fix among others — `fetch_program.py` failed with the
pre-fix `__NEXT_DATA__` parse error until the worktree was rebased onto local `master`
(clean, no conflicts; confirmed no functional overlap in the 2 shared touched files).

## Credit-pool spend (approximate)

`nightly.py` does not surface the adapter's per-call `cost=$…` log line in its terminal
output (no logging handler configured) — a usability gap worth a follow-up, separate from
hb-322. Based on directly-observed envelope costs during live debugging (cold-cache calls
~$0.20–0.24 each, this workspace's `sec-research/CLAUDE.md` auto-load dominating the cache-
creation cost), across roughly a dozen real `claude -p` invocations this session (Task 1's
spike, ad hoc debugging calls, the two pre-fix failed attempts, and the final clean
Step 3 + Step 4 runs), **total spend is approximately $2–3** — comfortably inside the
$20/month Pro-tier programmatic credit pool, with no out-of-pocket spill (verified
`ANTHROPIC_API_KEY` absent throughout via repeated positive checks).

## Disposition

hb-322's DoD is met: a trustworthy outcome was reached (defensible evidence-backed null
with full audit trail), via the real `claude-cli` provider, against a real loaded huntr
program. Closing the bead (Task 7 Step 1) — with the PoC-authoring validation gap above
filed as context for future runs, not a blocker to closure.
