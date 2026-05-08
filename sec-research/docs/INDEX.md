# Trace-ID Index

Append-only registry of every finding produced in this workspace, ordered by Trace ID. Maintained by `scripts/ledger_query.py --update-index`.

## Format

| Trace ID | Date | Title | Status | Venue | Submission ID |
|----------|------|-------|--------|-------|---------------|
| (no findings yet — Stage 1 just initialized) | | | | | |

## How this index is updated

- `PoT-1` hook auto-tags new findings with Trace IDs (format: `FIND-YYYY-MM-DD-NNN`)
- After each commit to `findings/`, `scripts/ledger_query.py --update-index` is run as part of post-commit (out of scope for Stage 1; Stage 1 has manual update via that command)

## How to query

```powershell
# All findings
python scripts/ledger_query.py --list

# By status
python scripts/ledger_query.py --status submitted

# By venue
python scripts/ledger_query.py --venue ghsa

# Full history of one finding (across ledger.jsonl events)
python scripts/ledger_query.py --trace FIND-2026-05-07-001
```
