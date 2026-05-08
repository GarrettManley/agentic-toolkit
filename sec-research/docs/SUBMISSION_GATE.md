# Submission Gate

Three-script split: **verify (mechanical) → sign-approval (HUMAN moment) → submit (mechanical)**. The split is deliberate — signing is the only step requiring human judgment; everything else is automation.

```
                  ┌── verify_finding.py <trace>            (schema + PoC repro + refs validate)
finding.md ──────┼── sign_approval.py <trace> --venue X    (HUMAN: shows summary, requires typed confirm)
                  └── submit.py --trace X --token Y        (PT-2 validates token; dispatches per venue)
```

## Step 1: `verify_finding.py <trace-id>`

Same checks as the G-1 pre-commit hook:
- Schema-validate `finding.md` frontmatter against `schema/finding.schema.json`
- Re-run all reference validations (CVE, package@version, commit SHAs)
- Run `findings/<trace>/poc/reproduce.sh` in sandbox; verify `expected_exit_code` and (if `deterministic: true`) `expected_output_hash`
- Verify `evidence/redacted/` is non-empty if class warrants it (per `evidence.schema.json`)
- Verify `timeline.md` exists and is append-only
- Write machine-readable result to `findings/<trace>/verification.json`

If any check fails: exit non-zero with structured error. `sign_approval.py` refuses to start without a clean `verification.json`.

## Step 2: `sign_approval.py <trace-id> --venue <venue>` (HUMAN moment)

Interactive — this is the only step that demands human judgment. Shows:

```
═══════════════════════════════════════════════════════════════
  APPROVAL REQUEST — Type the trace-id to confirm submission
═══════════════════════════════════════════════════════════════

  Trace ID    : FIND-2026-05-07-001
  Title       : SQL injection in acme-pkg parseQuery()
  Target      : acme-pkg@1.2.3 (npm)
  Vuln Class  : dependency-cve
  Severity    : CVSS v3.1 9.8 (Critical) — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
  Venue       : huntr (max payout $500)
  Dedup check : 2026-05-07T12:34Z — no matches across NVD, GHSA, OSV, huntr disclosed/

  AI assistance allowed: yes (program rules say so)
  AI disclosure required: yes (will be added to finding body)

  Citations:
    [1] github.com/acme-org/acme-pkg/blob/v1.2.3/src/parser.js#L42 (Tier 1)
    [2] https://owasp.org/www-community/attacks/SQL_Injection (Tier 1)

  PoC verification: PASSED (deterministic, expected exit 1, sandbox isolated)

  Type the trace-id below to confirm:
> _
```

If the user types the trace-id correctly, `sign_approval.py` writes a single-use HMAC-signed approval token to `submissions/tokens/<token-id>.json`. Issuance event appends to `submissions/ledger.jsonl`.

If the user types anything else, no token is written and the program exits without effect.

This is the **single point of human control** in the entire pipeline. The script will refuse to operate non-interactively (no `--no-confirm` flag exists by design).

## Step 3: `submit.py --trace <trace-id> --token <token-id>`

PT-2 hook validates that `--approval-token` references a valid signed token before letting the script run. If valid, dispatches per-venue:

### Stage 1 — Full implementations

| `--venue` value | Behavior |
|-----------------|----------|
| `manual-form` | Opens browser to program's submission URL; copies finding-body to clipboard; marks finding `submitted-manual` in frontmatter; appends ledger entry. Human pastes-in. |
| `ghsa` | Uses `gh api` POST to repo's `/security-advisories` endpoint. Leverages existing `gh auth login` credential — no keyring entry needed. Captures venue-assigned advisory ID into finding frontmatter. |

### Stage 7 — Will be filled in (currently stubbed)

| `--venue` value | Stage 1 stub behavior |
|-----------------|----------------------|
| `huntr` | Returns "Not implemented until Stage 7; use --venue manual-form for now" with exit code 2 |
| `ibb-h1`, `h1` | Same |
| `bugcrowd`, `intigriti` | Same |
| `direct-maintainer` | Same |

All dispatches (full or stubbed) append to `submissions/ledger.jsonl` regardless of outcome. The ledger is the source of truth for "did we attempt this?"

## What the ledger captures

Every entry conforms to `schema/submission.schema.json`:

```json
{
  "entry_id": "led-2026-05-07-014",
  "event_type": "submission-succeeded",
  "trace_id": "FIND-2026-05-07-001",
  "venue": "ghsa",
  "submitted_at": "2026-05-07T16:42:13Z",
  "submission_id": "GHSA-xxxx-yyyy-zzzz",
  "approval_token_id": "apv-2026-05-07-007",
  "outcome": "submitted",
  "outcome_at": "2026-05-07T16:42:14Z",
  "actor": "garrettmanley",
  "notes": "Submitted via gh api; auto-assigned ID returned."
}
```

`event_type` enum: override-issued / approval-issued / submission-attempted / submission-succeeded / submission-failed / status-transition.

Status transitions (e.g., `submitted → accepted`) are also ledger events, ensuring the ledger is a complete audit history of every interaction with the bounty pipeline.
