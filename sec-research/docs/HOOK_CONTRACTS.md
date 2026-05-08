# Hook Contracts

All hooks are **hard-block** (per workspace charter). The override mechanism is the auditable safety valve. Two rules have NO override path:

- **PT-2** (submission gate) — submission requires a human-signed approval token; nothing else gets through
- **PT-6 / G-2** (secret redaction) — secrets in evidence/redacted/ or staged commits must be redacted; never papered over with overrides

## Rule reference

| ID | Event | Triggers on | Blocks if... | Override |
|-----|-------|-------------|---------------|----------|
| **PT-1** | PreToolUse | HTTP/browser/fetch tool calls | target host not in any loaded `programs/<slug>/scope.yaml` | signed token |
| **PT-2** | PreToolUse | submission scripts / API calls to bounty venues | missing `--approval-token <id>` referencing valid signed token | **none — hard wall** |
| **PT-3** | PreToolUse | Edit/Write/MultiEdit | file_path resolves outside `sec-research/` | signed token |
| **PT-4** | PreToolUse | Edit/Write to `findings/**/*.md` | content has unverifiable CVE-ID, `pkg@version`, or commit SHA | signed token |
| **PT-5** | PreToolUse | Bash invoking PoC code or registry installs | doesn't go through `sandbox_server.py` | signed token |
| **PT-6** | PreToolUse | Edit/Write to `findings/**/evidence/redacted/**` | gitleaks-style scan finds API keys / AWS / JWT | **none — must redact** |
| **PoT-1** | PostToolUse | new `findings/<dir>/` created | (auto-correct: injects Trace-ID if missing) | n/a |
| **PoT-2** | PostToolUse | `findings/**/finding.md` written | a `Fact:`/`Claim:` line lacks `Citation:` + `Proof:` | signed token |
| **PoT-3** | PostToolUse | runtime tool calls in active finding | timeline.md write fails or evidence not captured | signed token |
| **S-1** | Stop | session has modified a finding | finding lacks PoC or schema-valid frontmatter AND isn't `status: draft-incomplete` | signed token |
| **S-2** | Stop | always | session log can't be written to `runtime/sessions/` | signed token |
| **UPS-1** | UserPromptSubmit | always | prompt mentions testing/recon/exploit AND no program scope loaded | injects load-program reminder |
| **UPS-2** | UserPromptSubmit | prompts naming hosts/URLs/packages/repos | identifier doesn't resolve to a loaded scope | signed token |
| **G-1** | git pre-commit | `findings/**/*` staged | `verify_finding.py` fails (schema, PoC repro, refs, evidence) | `--allow-incomplete` flag + signed token |
| **G-2** | git pre-commit | always (workspace-wide) | gitleaks scan finds secrets in staged content | **none — must redact** |
| **G-3** | git pre-push | always | G-1 + G-2 fail on any unpushed commit | (same as inner rule) |
| **G-4** | git commit-msg | `findings/` files staged | commit message lacks `Trace-ID:` line | signed token |

## Hook implementation notes

- All hooks are Python scripts: `hooks/{pretooluse,posttooluse,stop,userpromptsubmit}.py`
- Each hook is a dispatcher — it inspects the event payload, identifies which rule(s) apply, runs them in order, exits non-zero on first violation
- Hooks emit structured JSON to stderr: `{rule_id, action, target, reason, override_path}` — Claude can present clear actionable error messages
- Shared utilities live in `hooks/lib/` (sign_verify, scope_match, nvd_lookup, registry_lookup, git_lookup, secret_scan, schema_validate, credentials)

## Override mechanism (the auditable bypass)

Override tokens are HMAC-SHA256-signed JSON files at `overrides/signed/<token-id>.json`:

```json
{
  "token_id": "ovr-2026-05-07-001",
  "created_at": "2026-05-07T14:23:00Z",
  "created_by": "garrett",
  "rule_id": "PT-1",
  "scope": {
    "trace_id": "FIND-2026-05-07-001",
    "target": "registry.npmjs.org",
    "reason": "Querying public registry for package metadata"
  },
  "expires_at": "2026-05-07T18:23:00Z",
  "max_uses": 1,
  "signature": "<HMAC-SHA256 over canonical JSON>"
}
```

### Properties

- **Single-use by default**: `max_uses: 1`. Hard ceiling: 5.
- **Short-lived**: 4h TTL by default. Hard ceiling: 24h after `created_at`.
- **Signed via HMAC-SHA256** with key at `~/.claude/sec-research-override-key` — file outside the repo, gitignored anyway.
- **Sole issuance path**: `scripts/sign_override.py` — interactive y/n confirmation that prints the rule, target, and reason. No programmatic issuance from inside any agentic loop.
- **Used tokens** move to `overrides/used/` (gitignored). **Issuance + use events** append to `submissions/ledger.jsonl` so the audit trail survives even after token deletion.

### Why the key file lives outside the repo

If Claude (or any agent) ever subverts itself and tries to fabricate an override, it cannot sign the token without the HMAC key. Only a human with shell access to `~/.claude/sec-research-override-key` can. This is the single most important security property of the system: **overrides are out-of-band**.

### Override security tests

The test suite (`tests/hooks/test_override_*.py`) verifies:
- Forged tokens (hand-edited JSON) fail signature verification
- Single-use tokens cannot be reused (second use blocks)
- Expired tokens (now > expires_at) fail validation
- Tokens for the wrong rule_id don't permit a different rule

## Workspace scoping

The `.claude/settings.json` for `sec-research/` uses path matchers so all hooks **only fire when Claude's CWD is inside `sec-research/` or a tool call targets a path inside it**. Other workspace work is unaffected.
