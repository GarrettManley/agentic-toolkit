# Working-Tree Triage — 2026-05-07

Read-only triage of unrelated working-tree modifications in
`C:/Users/Garre/Workspace` after the Stage 1 sec-research/ commit on
`feature/sec-research-foundation`. The deleted `site/content/docs/toolkit/**`
files (~21 entries) are owned by a parallel agent and excluded here.

## Triage table

| Path | Classification | Reasoning | Recommended action |
|---|---|---|---|
| `sec-research/submissions/ledger.jsonl` | **Keep + commit** | 4 new `override-issued` events (led-005..008, 2026-05-08 03:32 & 04:01 UTC) appended by `sign_override.py` during legitimate post-commit override testing. This is exactly what the ledger is designed to capture; tail format matches the prior 4 baseline entries verbatim. Discarding them would erase a real audit trail. | Stage as small follow-up commit *inside* sec-research scope (G-1/G-4 don't apply — no `findings/` files staged). |
| `site/content/docs/001-workspace-foundation.md` | **Separate commit** | Substantive ADR rewrite: title changed to "Architecture of Hybrid Context Synthesis", section 2 (Token-Budgeted Discovery + Verification Traces) removed, dates re-stamped 2026-05-07. Continues the rebrand that landed in `be02df0`. | Land on a `docs/adr-rebrand-followup` branch. |
| `site/content/docs/002-local-orchestration.md` | **Separate commit** | Trivial date/Trace-ID bump (2026-03-30 → 2026-03-31). Pairs naturally with 001/003. | Same branch as 001. |
| `site/content/docs/003-local-script-autonomy.md` | **Separate commit** | Same trivial date/Trace-ID bump. | Same branch as 001. |
| `site/content/docs/toolkit/skills/citation-seeker/SKILL.md` | **Separate commit** | Real content edit (version 1.0.0 → 1.1.0, description tightened to mention Hybrid Context Synthesis). NOT a deletion — distinct from the parallel agent's work. | Same rebrand branch. |
| `site/layouts/shortcodes/experiment-metrics.html` | **Separate commit** | Functional shortcode upgrade: now resolves `data.json` from page Resources first, falling back to `Site.Data.experiments`. Implements section 3 of the academic-research-dashboard spec below. | Same rebrand branch (or its own "experiment-data-resources" commit). |
| `docs/superpowers/specs/2026-03-30-academic-research-dashboard-design.md` | **Investigate / commit-as-historical** | Finished IMRAD-format spec, dated 2026-03-30, signed `Verified by Gemini CLI`. Status field reads DRAFT but content is complete and the implementing change (`experiment-metrics.html` data-resources fallback) is already in the tree — so this spec is *post-facto historical record*. | Commit as-is to `docs/superpowers/specs/`. |
| `docs/superpowers/specs/2026-03-30-global-rebranding-design.md` | **Investigate / commit-as-historical** | Same shape — finished spec for the "Architecture of Hybrid Context Synthesis" rebrand. Status DRAFT but implementation already shipped via commits `be02df0`/`dc91168` and the ADR edits above. Stage 3 numbering ("Stage 4: Verification" with no Stage 3) is a minor cosmetic bug, not a blocker. | Commit as-is alongside the dashboard spec. |
| `site/.hugo_build.lock` | **Discard + gitignore** | Hugo's build mutex, recreated every build. Should never be tracked. | Add `.hugo_build.lock` to a new `site/.gitignore`. |
| `site/archetypes/default.md` | **Investigate** | `hugo new site` boilerplate (`title = '{{ replace .File.ContentBaseName ... }}'`). Never used by Hextra-themed content here. Likely accidental from a misfired `hugo new`. | Ask Garrett — if no archetypes are wanted, discard; if Hugo's archetype workflow will be used later, commit. |
| `site/hugo.toml.bak` | **Discard + gitignore** | A 3-line "My New Hugo Site" `baseURL='https://example.org/'` stub — pre-rebrand backup of `hugo.toml`. The current `hugo.toml` is the canonical config. The `.bak` is a one-shot editor backup. | Delete; add `*.bak` to a new `site/.gitignore`. |
| `site/public/` | **Discard + gitignore** | Hugo build output dir (`404.html`, fingerprinted assets, etc.). Regenerated on every `hugo` invocation; `publish.ps1` rebuilds it post-commit. | Add `public/` to a new `site/.gitignore`. |
| `site/themes/` | **Discard + gitignore** (vendored) | Contains `hextra/` (Hugo Hextra theme). Never tracked in this repo's history; no `.gitmodules`. Either the user installs it via `hugo mod`/manual clone, or it's a dev-machine convenience. Tracking it would copy ~thousands of upstream files. | Add `themes/` to a new `site/.gitignore`; document install in `site/README.md` or rely on `hugo mod get`. |

## Special findings

### `sec-research/submissions/ledger.jsonl`
The 4 appended lines have `entry_id` `led-2026-05-08-005` through `-008`,
all `event_type=override-issued`, all referencing `override_token_id=ovr-2026-05-08-001`,
`rule_id=PT-1`, `target=test.example.com`. They were written by
`scripts/sign_override.py` (which calls `lib.ledger.append_event` at line 141
of that script) during what looks like repeated test invocations of the
override flow at 03:32:07 UTC (×2) and 04:01:16/17 UTC (×2). The single
override token was reused multiple times, which is consistent with a
multi-use token (max_uses ≤ 5) being burned through a unit test loop.

This is **desired behavior** — the ledger is the workspace's tamper-evident
audit log per the charter, and tests legitimately exercise it. Keep and
commit. (Reusing a single token four times is a smoke-test artifact, not
a defect; the token's `used/` directory should reflect a corresponding
move once `max_uses` is reached.)

### `2026-03-30-academic-research-dashboard-design.md` & `2026-03-30-global-rebranding-design.md`
Both are **finished specs masquerading as DRAFT**. Each:
- Has full IMRAD-style structure (Objective, Architecture, Constraints,
  Success Criteria, Implementation Stages).
- Is signed `Verified by Gemini CLI on 2026-03-30`.
- Has its implementation already in the working tree (the ADR rebrand for
  the rebranding spec; the `experiment-metrics.html` Resources lookup for
  the dashboard spec).

Treat as historical record — commit verbatim to preserve the design
trail. The DRAFT status field is misleading but rewriting it would be
revisionist.

## Suggested next commands (PowerShell from `C:/Users/Garre/Workspace`)

```powershell
# 1. sec-research ledger update (small, isolated, on current branch)
git add sec-research/submissions/ledger.jsonl
git commit -m "chore(sec-research): record override-test ledger entries 005-008"

# 2. Site rebrand follow-up commit (new branch)
git switch -c docs/adr-rebrand-followup
git add site/content/docs/001-workspace-foundation.md `
        site/content/docs/002-local-orchestration.md `
        site/content/docs/003-local-script-autonomy.md `
        site/content/docs/toolkit/skills/citation-seeker/SKILL.md `
        site/layouts/shortcodes/experiment-metrics.html
git commit -m "docs(site): finish hybrid-synthesis rebrand on ADRs 001-003 + citation-seeker"

# 3. Capture the historical specs
git add docs/superpowers/specs/2026-03-30-academic-research-dashboard-design.md `
        docs/superpowers/specs/2026-03-30-global-rebranding-design.md
git commit -m "docs(specs): archive 2026-03-30 dashboard + rebranding design specs"

# 4. Add a site-scoped gitignore for build artifacts (NEW file, allow-listed by root)
#    Root .gitignore is allow-list style (only sec-research/, site/, etc. permitted),
#    so a nested site/.gitignore is the cleanest place to drop these patterns.
@'
public/
themes/
.hugo_build.lock
*.bak
'@ | Set-Content site/.gitignore -Encoding utf8
git add site/.gitignore
git commit -m "chore(site): ignore Hugo build artifacts (public/, themes/, *.bak, lock)"

# 5. Decide on archetypes/default.md interactively, then either:
#    a) commit it     -> git add site/archetypes/default.md && git commit -m "chore(site): keep default archetype"
#    b) discard it    -> Remove-Item site/archetypes/default.md
```

After running 1-4, expect `git status` to show only `site/archetypes/default.md`
pending Garrett's decision and the parallel agent's deletions still to triage.
