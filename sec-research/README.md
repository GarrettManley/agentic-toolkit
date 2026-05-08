# sec-research/

A hard-bounded, evidence-disciplined security-research workspace whose purpose is to produce **reproducible, Tier-1-citable findings** that pass human review before submission to bug bounty programs.

**Status**: Stage 1 of 7 (foundation/governance only — see `docs/CHARTER.md` for full roadmap)

## Three Invariants (enforced by hooks)

1. **Scope-bounded** — every network call, file write outside this dir, and target identifier must trace back to a loaded `programs/<slug>/scope.yaml`. No exceptions without a signed override token.
2. **Evidence-grounded** — no claim ships without (a) `Citation:` (Tier-1 source), (b) runnable PoC, (c) captured execution evidence.
3. **Human-gated** — every submission requires a human-signed approval token. Drafts auto-generated; sends never.

## Quickstart

This is a standalone Claude Code workspace — open Claude with `sec-research/` as the working directory, and run all commands from inside it.

```powershell
# (one-time) cd into the workspace
Set-Location C:\Users\Garre\Workspace\sec-research

# 1. Verify workspace is healthy
python scripts\init_workspace.py --verify

# 2. Load a program scope (Stage 2 will provide automated intake)
python scripts\load_program.py --venue ghsa --identifier <repo-slug>

# 3. On-demand investigation
python scripts\investigate.py <program-slug> --asset <identifier>

# 4. Pre-submission flow (HUMAN required at sign_approval)
python scripts\verify_finding.py <trace-id>
python scripts\sign_approval.py <trace-id> --venue <venue>
python scripts\submit.py --trace <trace-id> --token <token-id>
```

## Where things live

| Path | Purpose |
|------|---------|
| `docs/` | Charter, hook contracts, schemas, evidence discipline, submission gate, credential handling |
| `schema/` | JSON Schemas for program, finding, evidence, override, submission |
| `hooks/` | PreToolUse / PostToolUse / Stop / UserPromptSubmit + lib/ utilities |
| `programs/<slug>/` | Loaded program scopes (one dir per program) |
| `findings/<trace>/` | Persistent record: finding.md + poc/ + evidence/ + timeline.md |
| `playbooks/` | Self-improvement substrate (class playbooks + meta) |
| `submissions/ledger.jsonl` | Append-only audit log of every submission/override event |
| `overrides/signed/` | Active HMAC-signed override tokens |
| `runtime/` | **Gitignored**: sandbox output, raw recon, briefings, caches |
| `scripts/` | All workspace executables |
| `tests/` | Hook integration tests + schemas + e2e smoke |

## Override key

The HMAC key for signing override + approval tokens lives at `~/.claude/sec-research-override-key` (outside this repo). Generate via:

```powershell
# One-time setup
python -c "import secrets; print(secrets.token_hex(32))" > $HOME\.claude\sec-research-override-key
```

Loss of this key = no overrides possible until a new key is generated. By design.

## Stage 1 vs Stages 2-7

Stage 1 is foundation only. See `docs/CHARTER.md` § Roadmap. Stages 2-7 each get their own spec/plan cycle and build on Stage 1's hook contracts and schemas without modifying them.
