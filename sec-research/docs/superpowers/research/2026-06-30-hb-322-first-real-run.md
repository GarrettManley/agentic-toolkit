# hb-322: First Real Supervised Run — Outcome (2026-06-30)

**Tracker:** hb-322 (P1, sec-research's first real end-to-end run vs huntr.com, supervised, trustworthy outcome).

**Correction note:** this document's first version claimed a trustworthy null based on two
runs that were, in fact, **masked LLM failures** — caught by the final whole-branch code
review, which flagged that the "trustworthy null" claim wasn't evidenced against the
ledger. Investigating that flag surfaced a real bug (see below) that this corrected version
documents alongside the genuinely-validated re-run. The lesson stands on its own: a "clean"
journal checkpoint is not sufficient evidence of a reasoned model decision — the ledger's
absence of `hypothesis-llm-unavailable`/`hypothesis-parse-error` events is the actual proof.

## Terminal outcome (final, ledger-verified)

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

**Ledger verification (the actual evidence the null is trustworthy):** queried
`submissions/ledger.jsonl` for all entries with `slug == "huntr-isaacs-minimatch"` logged
after this run's start (`2026-06-30T20:36:10Z`) — **zero entries**. `generate_hypotheses`
(`llm/generate.py:134-185`) has six silent-drop paths (`hypothesis-llm-unavailable`,
`hypothesis-parse-error`, `hypothesis-target-divergence`, `hypothesis-version-unresolved`,
`hypothesis-invalid`, `hypothesis-out-of-scope`), each logging to this ledger before
`continue`ing; zero entries of any of the six rules out every one. The `0` hypotheses
reflects a genuine model decision (`{"hypotheses": []}`, confirmed verbatim via direct reproduction below),
not a swallowed failure.

## Why the null is trustworthy

Recon resolved `minimatch@10.2.5` and surfaced 9 `known_advisories` from the lockfile scan
— but every one of them targets a **transitive** dependency (`brace-expansion`, `tar`,
`uuid`, `ws` ×2, `markdown-it`, `linkify-it`, `ip-address`, `@sigstore/core`), none targets
`minimatch` itself. The single eligible playbook
(`dependency-cve/known-advisory-confirmation`) explicitly scopes v1 to the **direct**
asset (negative signal: "The advisory targets a different package than the asset
(transitive-only; v1 targets the direct asset)"). The model — running through the new
`claude-cli` provider, with MCP/tool access fully disabled (see bugs below) — correctly
declined to mis-target a transitive advisory onto `minimatch`, producing a genuine
`{"hypotheses": []}` rather than a fabricated finding. This is the evidence-grounded
behavior `sec-research/CLAUDE.md` requires, confirmed working under a real external target.

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
  reliably author discriminating PoCs — remains untested by this run.** Filed on the
  follow-up bead (hb-5i3) as the actual validation point for the next real run.

## Three live-discovered bugs, fixed mid-run

The first attempts failed or silently produced masked nulls. All three are now covered by
regression tests; full suite 439 passed, 6 skipped, post-fix.

1. **Tool-use turn exhaustion (commit `5fed247`).** Without `--tools ""`, the model
   invoked a built-in tool (`ToolSearch`) instead of answering directly with JSON against
   the real production prompt — burning the single allowed turn (`--max-turns 1`) with no
   final text result, exiting non-zero with `subtype: "error_max_turns"`. Fixed by adding
   `--tools ""` to `build_argv()`.
2. **Unsound failure classification (commit `5fed247`).** `_classify_failure`
   keyword-searched the *entire* stdout blob (which on any non-zero exit still carries the
   full session-init event — every tool, MCP server, and plugin name in the *calling*
   session). An MCP server literally named `"...Intuit Credit Karma"` matched the
   `"credit"` keyword, misclassifying the unrelated `error_max_turns` failure as
   pool-exhaustion. Fixed: check the structured `rate_limit_event.rate_limit_info.status`
   first, fall back to keyword-matching `stderr` only — never `stdout`.
3. **Inherited MCP servers (commit `a0f5b8b`, found via the final code review's flag).**
   `--tools ""` only disables the *built-in* tool set — `claude -p` still inherits every
   MCP server the **calling session** has connected (Gmail, Spotify, Google Drive, ...).
   Even after fix #1, the model invoked an inherited MCP tool (Spotify "Search"), which
   hit a transient Cloudflare 502 on `mcp-proxy.anthropic.com`, again burning the single
   turn → `error_max_turns`. This time `generate_hypotheses`' per-item `LLMUnavailable`
   catch (`generate.py:134-137`) silently swallowed it as a "clean" zero-hypotheses
   result — the ledger showed `hypothesis-llm-unavailable` for both affected runs, which
   is exactly the masking the final review's documentation-gap finding asked to rule out.
   Fixed by adding `--strict-mcp-config` (with no `--mcp-config`) to `build_argv()`,
   dropping every inherited MCP server. Confirmed via direct reproduction: the call now
   returns a clean `subtype: "success"`, `result: '{"hypotheses": []}'`.

## Worktree base-staleness (unrelated but blocking, fixed mid-run)

The execution worktree branched from `origin/master` (9 commits behind local `master`),
missing the hb-dzu huntr-fetcher fix among others — `fetch_program.py` failed with the
pre-fix `__NEXT_DATA__` parse error until the worktree was rebased onto local `master`
(clean, no conflicts; confirmed no functional overlap in the 2 shared touched files).

## Credit-pool spend (approximate)

`nightly.py` does not surface the adapter's per-call `cost=$…` log line in its terminal
output (no logging handler configured) — a usability gap worth a follow-up, separate from
hb-322. Based on directly-observed envelope costs during live debugging (cold-cache calls
~$0.16–0.24 each, this workspace's `sec-research/CLAUDE.md` auto-load dominating the
cache-creation cost), across roughly 15 real `claude -p` invocations this session (Task 1's
spike, ad hoc debugging calls, three pre-fix failed/masked attempts, and the final two
clean Step 3 + Step 4 runs), **total spend is approximately $2.50–3.50** — comfortably
inside the $20/month Pro-tier programmatic credit pool, with no out-of-pocket spill
(verified `ANTHROPIC_API_KEY` absent throughout via repeated positive checks).

## Disposition

hb-322's DoD is met: a trustworthy outcome was reached (defensible evidence-backed null
with full audit trail, now ledger-verified against masking) via the real `claude-cli`
provider, against a real loaded huntr program. The bead is closed — with the PoC-authoring
validation gap and the masking-detection lesson both filed as context (hb-5i3 and this
document) for the next real run.
