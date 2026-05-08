# Engineering Specification: `sec-research/` Foundation & Governance Workspace

**Standard:** IEEE 830-1998 (Software Requirements) + ISO/IEC 25059:2026 (Quality model for AI systems) | **Trace ID:** trace-20260507-001
**Status:** APPROVED | **Author:** Claude (Opus 4.7) | **Date:** 2026-05-07
**Stage:** 1 of 7 | **Plan File:** `~/.claude/plans/i-m-looking-to-create-glimmering-octopus.md`

---

## 1. Objective

Establish a hard-bounded, evidence-disciplined security-research workspace at `C:\Users\Garre\Workspace\sec-research\` whose purpose is to produce reproducible, Tier-1-citable findings that pass human review before submission to bug bounty programs (huntr.com, GHSA, IBB on HackerOne, direct maintainer disclosure). v1 anchors on **OSS supply-chain and dependency vulnerabilities** because findings naturally tie to commit hashes and package versions, making them Tier-1 citable by construction and the lowest-risk path to passing the no-AI-slop bar.

This Stage delivers the **foundation/governance layer only** — schemas, hooks, override mechanism, scheduling integration, submission gate, and the self-improvement substrate's storage layer. Stages 2-7 (program intake → recon → hypothesis & test harness → triage & dedup → report drafting → submission pipeline maturation) each build on Stage 1's contracts without modifying them.

## 2. Three Workspace Invariants (Enforced by Hooks)

1. **Scope-bounded** — every network call, file write outside the workspace, and target identifier must trace back to a loaded `programs/<slug>/scope.yaml`. No exceptions without a signed override token.
2. **Evidence-grounded** — no claim ships to a finding draft without (a) a `Citation:` (Tier-1 source), (b) a runnable PoC, and (c) captured execution evidence. Extends the existing `citation-seeker` skill's rule.
3. **Human-gated** — every submission requires a human-signed approval token. Drafts can be auto-generated; sends cannot.

## 3. Architecture (Approach A — Self-contained workspace)

Single top-level `sec-research/` directory with workspace-scoped `.claude/settings.json` so hard-block hooks fire only inside this workspace. Reuses existing infrastructure (`fast_orchestrator.py`, `sandbox_server.py`, `truth-seeker` and `citation-seeker` skills, the `schedule` skill) without duplication. Coexists with global hookify hooks via path matchers.

Directory layout (canonical — see plan for detailed annotation):

```
sec-research/
├── README.md, .claude/, .gitignore, .hugoignore-marker
├── docs/        # CHARTER, HOOK_CONTRACTS, SCOPE_SCHEMA, EVIDENCE_DISCIPLINE,
│                # SUBMISSION_GATE, PLAYBOOK_FORMAT, CREDENTIAL_HANDLING, INDEX
├── schema/      # 5 JSON Schemas: program, finding, evidence, override, submission
├── hooks/       # PreToolUse, PostToolUse, Stop, UserPromptSubmit + lib/ utilities
├── programs/    # <slug>/scope.yaml, targets.txt, disclosed/
├── findings/    # YYYY-MM-DD-<trace>-<slug>/finding.md + poc/ + evidence/ + timeline.md
├── playbooks/   # _meta/{accepted,rejected,dedup-pitfalls}.md + <class>/<technique>.md
├── submissions/ # ledger.jsonl + tokens/
├── overrides/   # pending/ + signed/ + used/(gitignored)
├── runtime/     # GITIGNORED ENTIRELY: sandbox/, recon/, briefings/, sessions/,
│                # feedback-queue.jsonl, scheduled-runs.jsonl, cache/{nvd,registry,git}/
├── scripts/     # init_workspace, nightly, investigate, verify_finding, load_program,
│                # sign_override, sign_approval, submit, ledger_query, setup_credentials,
│                # run_nightly.ps1, briefing_ping
└── tests/       # hooks/, schemas/, e2e/, fixtures/
```

## 4. Hook Contracts (Hard-Block Everywhere)

All hooks emit non-zero exit on violation. Override = HMAC-SHA256-signed token stored at `overrides/signed/<token>.json`, key file at `~/.claude/sec-research-override-key` (outside repo). Two rules have NO override path: PT-2 (submission gate) and PT-6 / G-2 (secret redaction).

| ID | Event | Blocks if... | Override |
|-----|-------|---------------|----------|
| PT-1 | PreToolUse (HTTP/browser/fetch) | target host not in any loaded scope | signed |
| PT-2 | PreToolUse (submission scripts/APIs) | missing `--approval-token <id>` | **none — hard wall** |
| PT-3 | PreToolUse (Edit/Write) | path resolves outside `sec-research/` | signed |
| PT-4 | PreToolUse (writes to findings/**.md) | unverifiable CVE/`pkg@version`/commit SHA | signed |
| PT-5 | PreToolUse (Bash invoking PoC/installs) | doesn't go through `sandbox_server.py` | signed |
| PT-6 | PreToolUse (writes to evidence/redacted/) | gitleaks finds API keys/AWS/JWT | **none — must redact** |
| PoT-1 | PostToolUse (new finding dir) | (auto-correct: injects Trace-ID) | n/a |
| PoT-2 | PostToolUse (writes to finding.md) | Fact/Claim line lacks Citation+Proof | signed |
| PoT-3 | PostToolUse (runtime tool calls) | timeline.md write fails / evidence missing | signed |
| S-1 | Stop | finding modified but missing PoC/schema-valid frontmatter | signed |
| S-2 | Stop | session log can't be written | signed |
| UPS-1 | UserPromptSubmit | testing/recon prompt with no scope loaded | injects reminder |
| UPS-2 | UserPromptSubmit | identifier doesn't resolve to loaded scope | signed |
| G-1 | git pre-commit | `verify_finding.py` fails on staged finding | `--allow-incomplete` + signed |
| G-2 | git pre-commit | gitleaks finds secrets | **none — must redact** |
| G-3 | git pre-push | G-1+G-2 fail on unpushed commits | (inner rules) |
| G-4 | git commit-msg | findings/ commit lacks `Trace-ID:` line | signed |

## 5. Schemas (`schema/*.json`)

- **`program.schema.json`**: scope, venue (enum: huntr/ghsa/ibb-h1/h1/bugcrowd/intigriti/direct-maintainer), in/out_of_scope[], rules{ai_assistance_allowed, ai_disclosure_required, rate_limit_per_min, embargo_period_days}, submission{protocol, endpoint, auth_ref{service, username}}.
- **`finding.schema.json`**: trace_id (`FIND-YYYY-MM-DD-NNN`), title, vuln_class (enum), severity{cvss_v3_1_vector required, cvss_v4_* optional}, status (10-state lifecycle: draft-incomplete → ... → submitted → {accepted,rejected,duplicate,informational}), target{asset_type, identifier, version_or_revision}, evidence{paths}, poc{reproduce_script, expected_exit_code, expected_output_hash, deterministic, preconditions}, citations[]≥1 (claim, source_url, source_tier 1|2|3, corroborator_url required if tier===3, accessed_at), deduplication_check{checked_against, matches, checked_at}.
- **`evidence.schema.json`**: class-keyed required fields. Stage 1 anchor `dependency-cve` requires package_ecosystem, package_name, affected_versions_range, fixed_version, vulnerable_function_path, cve_id_proposed_or_assigned, attack_vector. `supply-chain-malicious-pkg` requires package_ecosystem, malicious_version, payload_type, delivery_mechanism, c2_indicator.
- **`override.schema.json`**: token_id, created_at/by, rule_id, scope{trace_id, target, reason}, expires_at (≤now+24h), max_uses (≤5), HMAC-SHA256 signature.
- **`submission.schema.json`**: append-only ledger entries with event_type enum (override-issued/approval-issued/submission-attempted/submission-succeeded/submission-failed/status-transition).

## 6. Override Mechanism

```json
{
  "token_id": "ovr-2026-05-07-001",
  "created_at": "2026-05-07T14:23:00Z",
  "created_by": "garrett",
  "rule_id": "PT-1",
  "scope": {"trace_id": "FIND-2026-05-07-001", "target": "registry.npmjs.org", "reason": "..."},
  "expires_at": "2026-05-07T18:23:00Z",
  "max_uses": 1,
  "signature": "<HMAC-SHA256 over canonical JSON>"
}
```

Single-use by default, max 4h TTL (configurable per-token, hard ceiling 24h / 5 uses). Sole issuance path: `scripts/sign_override.py` (interactive y/n confirm). Used tokens move to `overrides/used/` (gitignored). Issuance + use events appended to `submissions/ledger.jsonl` for audit even after token deletion.

## 7. Scheduling — Hybrid

**Local heavyweight — Windows Task Scheduler**: `schtasks /Create` registers `pwsh -File sec-research/scripts/run_nightly.ps1` daily. The wrapper invokes `python scripts/nightly.py` with full filesystem access (programs/, runtime/, override-key, keyring credentials). All hooks fire normally; over-strict beats AI-slop.

**Cloud-side notification — `schedule` skill (RemoteTrigger)**: separate routine runs `briefing_ping.py` ~30 min after typical nightly completion. Reads latest `runtime/briefings/<date>.md`, summarizes counts, sends notification. Cloud agent never touches local FS — consumes briefing artifact only.

Both entry points (`nightly.py` + on-demand `investigate.py`) share the same 7-step pipeline (refresh scopes → refresh disclosed → recon → hypothesize → verify → draft → briefing). Stage 1 ships these as **skeletons** — pipeline framework with stages 3-5 returning fixture data. The hooks, ledger, and verification all exercise as if real work happened.

## 8. Submission Gate

Three-script split: **verify (mechanical) → sign-approval (HUMAN moment) → submit (mechanical)**.

`sign_approval.py` is the only place a human decision is required. Interactive: shows trace-id/title/target/severity (CVSS v3.1)/venue/expected payout/dedup timestamp, requires user to *type* the trace-id to confirm, generates a single-use approval token signed by the same HMAC key as overrides.

`submit.py` per-venue dispatch — **Stage 1 vs Stage 7 boundary**:
- **Full in Stage 1**: `--venue manual-form` (opens browser, marks submitted-manual), `--venue ghsa` (uses `gh api` POST to `/security-advisories` — leverages existing `gh` CLI auth)
- **Stub in Stage 1, full in Stage 7**: `--venue huntr|ibb-h1|h1|bugcrowd|intigriti|direct-maintainer`

Every dispatch (full or stubbed) appends to `submissions/ledger.jsonl`.

## 9. Credential Storage

Library: Python `keyring` → Windows Credential Manager (DPAPI-protected). `program.schema.json`'s `submission.auth_ref` is `{service, username}` resolved via `hooks/lib/credentials.py::get_credential(auth_ref)`. **Stage 1 needs ZERO populated credentials** — `gh api` (GHSA dispatch) uses `gh` CLI's existing auth. Keyring infrastructure built and tested against fixture credentials only.

## 10. Hugo-Leak Prevention

**Verified during implementation**: `publish_toolkit.py` walks only `.ai/skills/` and `.ai/scripts/`; `generate_spec.py` walks only `.ai/adr/`; Hugo content roots only at `site/content/`. Since `sec-research/` lives at workspace root (not under any of these), it's naturally excluded from publishing.

Defense-in-depth measures still implemented:
1. Add `!sec-research/` to root `.gitignore` (allow-list style requires explicit allow); add `sec-research/runtime/`, `sec-research/findings/**/evidence/raw/`, `sec-research/overrides/used/`, `sec-research/submissions/tokens/` as denials.
2. Modify `publish.ps1` to skip-publish when only `sec-research/` paths changed (avoids unnecessary Firebase redeploys on every finding-draft commit).

## 11. Reuse Map

| Existing asset | Path | Reuse |
|----------------|------|-------|
| `truth-seeker` skill (Tier 1/2/3) | `site/content/docs/toolkit/skills/truth-seeker/` | citations[] tiers; PT-4 enforces VERIFICATION_GUIDE rules |
| `citation-seeker` skill | `site/content/docs/toolkit/skills/citation-seeker/` | finding.md `Fact:/Citation:/Proof:` syntax; PoT-2 validates |
| `fast_orchestrator.py` | `.ai/scripts/fast_orchestrator.py` | Loop engine for nightly+investigate (Stage 4+) |
| `sandbox_server.py` | `.ai/scripts/sandbox_server.py` | All PoC repro + registry installs; PT-5 enforces |
| `steward.py` | `.ai/scripts/steward.py` | nightly.py copies refresh→audit→delegate→log structure |
| `verify_sync.ps1` | `.ai/scripts/verify_sync.ps1` | verify_finding.py adapts the schema+repro+refs validate pattern |
| `schedule` skill | global plugin | Cloud-side briefing_ping routine |

**Known limitation (Stage 4 prerequisite)**: `fast_orchestrator.py` runs subprocesses directly via `subprocess.run`. Claude's PreToolUse hooks do NOT intercept its commands. Stage 1 unaffected (skeleton doesn't loop); Stage 4 must add a subprocess-level scope-check wrapper before live testing.

## 12. Stage 1 vs Stages 2-7 Roadmap

| Stage | Scope | Depends on |
|-------|-------|-----------|
| **1 (this spec)** | Foundation: hooks, schemas, override, submission gate, scheduling, scaffolding | nothing |
| 2 | Program Intake (venue scope fetchers) | Stage 1 schemas |
| 3 | Recon Module (OSS pkg metadata, dep graph, repo clone, prior advisories) | Stage 2 |
| 4 | Hypothesis & Test Harness (LLM hypothesizes; sandboxed verification) | Stage 3 + sandbox |
| 5 | Triage & Dedup (NVD + GHSA + OSV + program disclosed/) | Stage 4 |
| 6 | Report Drafting (class-specific venue-format templates) | Stage 5 |
| 7 | Submission maturation + Self-improvement maturation | Stage 6 |

Stage 1 ships full hook scripts, all schemas, full submission gate (against GHSA + manual-form), skeleton nightly/investigate, all tests. Stages 2-7 each get their own spec/plan cycle.

## 13. Success Criteria

Stage 1 is complete when:
1. All A–F verification tests pass (see Plan § Verification).
2. End-to-end smoke: program load → investigate → draft → verify → sign-approval → submit-via-GHSA-mock → ledger record → status transition.
3. Every documented hook blocks at least one synthetic violation in tests.
4. Override mechanism is auditable: every issuance + use in `submissions/ledger.jsonl`.
5. Hugo never publishes any `sec-research/` content (verified end-to-end with a test commit).
6. Windows Task Scheduler entry runs `nightly.py` skeleton successfully and produces a briefing.
7. This spec doc lives at the documented path and is committed.
8. Charter, invariants, hook contracts, and override mechanism documented clearly enough that a researcher can pick up the workspace without re-reading the source code.

## 14. Implementation Stages (matches Plan § Implementation Sequence)

1. Spec doc (this file) — **DONE in this commit**
2. Hugo-leak fixes (.gitignore allow `!sec-research/`, publish.ps1 skip-guard)
3. Workspace scaffold via `init_workspace.py` (idempotent)
4. Hook lib utilities (sign_verify, scope_match, nvd_lookup, registry_lookup, git_lookup, secret_scan, schema_validate, credentials)
5. Hook dispatchers + workspace `.claude/settings.json`
6. Workspace scripts (verify_finding, sign_override, sign_approval, submit, load_program, ledger_query, setup_credentials)
7. Skeleton nightly.py + investigate.py + run_nightly.ps1
8. Git hooks (pre-commit, pre-push, commit-msg)
9. Tests + fixtures + e2e smoke
10. Windows Task Scheduler registration + briefing_ping cloud routine
11. Feature-branch commit; PR open

## 15. Reproducibility (Pass^k = TBD until smoke runs)

- All hooks have automated tests with fixed inputs
- Override token signing is deterministic (HMAC over canonical JSON)
- Schema validation is deterministic
- PoC reproduction must declare `deterministic: true|false` in finding frontmatter; non-deterministic PoCs require additional rationale
- Trace IDs make every finding linkable across git history, ledger, and playbooks

---

*Trace ID: trace-20260507-001 — see plan file for full implementation sequence and verification matrix.*
