# Charter: `sec-research/`

**Trace ID**: trace-20260507-001 (Stage 1 of 7)
**Status**: APPROVED 2026-05-07
**Spec**: `docs/superpowers/specs/2026-05-07-sec-research-foundation-design.md`

## What this workspace is for

`sec-research/` is a hard-bounded, evidence-disciplined security-research workspace whose purpose is to produce **reproducible, Tier-1-citable findings** that pass human review before submission to bug bounty programs. v1 anchors on **OSS supply-chain and dependency vulnerabilities** (huntr.com, GitHub Security Advisories, IBB on HackerOne, direct upstream maintainer disclosure).

## What this workspace is NOT for

- Web app DAST against blackbox targets — not v1 anchor (Stage 6+ may add)
- Detection evasion or red-team operations
- Any testing of targets not represented by an explicitly loaded `programs/<slug>/scope.yaml`
- Storing live credentials in plaintext (use `keyring` → Windows Credential Manager — see `CREDENTIAL_HANDLING.md`)

## The three workspace invariants

These are enforced by hooks; violation hard-blocks the offending action.

1. **Scope-bounded** — every network call, file write outside this workspace, and target identifier must trace back to a loaded `programs/<slug>/scope.yaml`. No exceptions without a signed override token.
2. **Evidence-grounded** — no claim ships to a finding draft without (a) a `Citation:` (Tier-1 source per `truth-seeker` rules), (b) a runnable PoC at `findings/<trace>/poc/reproduce.sh`, (c) captured execution evidence (timeline.md + redacted/ artifacts).
3. **Human-gated** — every submission requires a human-signed approval token. Drafts can be auto-generated; sends cannot.

## The seven-stage roadmap

| Stage | Scope | Status |
|-------|-------|--------|
| **1** | **Foundation: hooks, schemas, override mechanism, submission gate, scheduling, scaffolding** | **In progress** |
| 2 | Program Intake — venue scope fetchers (huntr API, GHSA, IBB) | Pending |
| 3 | Recon Module — OSS pkg metadata, dep graph, repo clone, prior advisories | Pending |
| 4 | Hypothesis & Test Harness — LLM hypothesizes; sandboxed deterministic verification | Pending |
| 5 | Triage & Dedup — NVD + GHSA + OSV + program disclosed/ + venue dupe APIs | Pending |
| 6 | Report Drafting — class-specific venue-format templates | Pending |
| 7 | Submission maturation + Self-improvement maturation | Pending |

None of stages 2-7 modify Stage 1's hook contracts or schemas. Stage 1 is the contract.

## Reuse map (existing infra this workspace builds on)

| Existing asset | Path | How reused |
|----------------|------|-----------|
| `truth-seeker` skill | `site/content/docs/toolkit/skills/truth-seeker/` | citation tier system; PT-4 enforces VERIFICATION_GUIDE rules |
| `citation-seeker` skill | `site/content/docs/toolkit/skills/citation-seeker/` | `Fact:/Citation:/Proof:` syntax in finding.md; PoT-2 validates |
| `fast_orchestrator.py` | `.ai/scripts/fast_orchestrator.py` | Loop engine for nightly+investigate (Stages 4+) |
| `sandbox_server.py` | `.ai/scripts/sandbox_server.py` | All PoC repro + registry installs; PT-5 enforces |
| `steward.py` | `.ai/scripts/steward.py` | nightly.py mirrors refresh→audit→delegate→log structure |
| `verify_sync.ps1` | `.ai/scripts/verify_sync.ps1` | verify_finding.py adapts schema+repro+refs validation pattern |
| `schedule` skill | global plugin | Cloud-side `briefing_ping.py` routine |
| Spec format | `docs/superpowers/specs/` | This workspace's spec follows IEEE/ISO + Trace ID conventions |

## Known limitation (Stage 4 prerequisite)

`fast_orchestrator.py` runs subprocesses directly via `subprocess.run`. **Claude's PreToolUse hooks do NOT intercept its commands.** Stage 1 unaffected (skeleton doesn't actually loop). Stage 4 must add a subprocess-level scope-check wrapper before live testing happens.
