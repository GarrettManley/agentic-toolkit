# hw-dashboard

Evidence-based PC-hardware **upgrade-planning dashboard** for a single machine
(this box: i7-14700F / 32 GB DDR5 / RTX 4060 **8 GB** on an MSI B760 board). It
answers: *what* to upgrade, *whether it fits*, and *when to buy* — every claim
cited, every price forecast confidence-scaled to how much history exists.

## Architecture (3 layers, 2 cadences)

| Layer | What | Cadence |
|-------|------|---------|
| **Collector** (`collector/`) | stdlib + `requests`; re-fetches tracked SKU prices, validates against `schema/`, appends idempotently to `data/series/<sku>.jsonl` | nightly (Task Scheduler) |
| **Analytics** (`analytics/`) | pure-stdlib signals → best-time-to-buy with history-scaled confidence; writes `data/analytics/` | on price change / recompute |
| **API** (`api/`) | FastAPI on `127.0.0.1`; serves profile/components/series/analytics/recommendation; webhook intake + recompute | always (when serving the SPA) |
| **Agent team + workflow** (`.claude/agents/`, `workflows/`) | reusable subagents (scout → spec → adversarial-verify → compat → forecast → strategist) orchestrated by the dynamic Workflow; emits `recommendation.json` | weekly / on-demand |
| **Frontend** (`web/`) | Vite + React + TS SPA; WCAG 2.1 AA | — |

The nightly Python job does cheap deterministic fetching; the LLM agents do the
expensive judgment (discovery, citation-verified specs, compatibility, ranking).

## Setup

```powershell
# Python backend (uv manages the venv from pyproject.toml)
uv run --extra dev pytest          # 34 tests, all offline
uv run python scripts/detect_machine.ps1   # (run the .ps1 directly) -> data/machine_profile.json
```

Detect the current machine (measured via CIM, not guessed — resolves DDR gen,
VRAM via nvidia-smi, friendly socket):

```powershell
pwsh -NoProfile -File scripts/detect_machine.ps1
```

## Run the dashboard locally

```powershell
# 1. API (from apps/hw-dashboard/)
$env:PYTHONPATH = "."
uv run uvicorn api.server:app --host 127.0.0.1 --port 8077

# 2. SPA (from apps/hw-dashboard/web/, proxies /api -> 127.0.0.1:8077)
npm install ; npm run dev
```

`scripts/seed_demo_data.py` writes example price history for the two seeded
components so the dashboard renders before live tracking accumulates.

## Refresh the recommendation (on-demand)

Run the **upgrade-dashboard** workflow (`workflows/upgrade-dashboard.workflow.js`)
via the Workflow tool, passing the machine profile as `args`. It returns an
`UpgradeRecommendation`; persist it to `data/recommendation.json`. Requires
`FIRECRAWL_API_KEY` for the monitor/scrape paths (discovery also uses built-in
WebSearch/WebFetch/deep-research).

## Schedule nightly price collection

```powershell
pwsh -NoProfile -File scripts/register_nightly.ps1          # daily 03:15 MT
pwsh -NoProfile -File scripts/register_nightly.ps1 -Unregister
```

## Data layout

- **Tracked (git):** `schema/`, `data/components/`, `data/skus/`, `data/seed/`, `data/machine_profile.json`
- **Local runtime (gitignored):** `data/series/`, `data/analytics/`, `data/intake/`, `data/recommendation.json`, `data/collector-runs.jsonl`

## Honesty notes

- Forecasts in the first ~2 weeks of first-party tracking are **weak** and labeled
  so (confidence scales with `history_days`; seed-only history is capped low).
- Retailer HTTP parsing is best-effort (anti-bot); firecrawl-monitor is the robust
  recurring path. A parser that can't extract a price returns `None` + a warning,
  never crashing the run.
