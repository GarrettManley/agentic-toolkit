"""Local read-mostly API over the collector-written data tree. Binds 127.0.0.1.

Serves component/SKU/series/analytics JSON to the SPA, recomputes analytics on
demand, and accepts firecrawl-monitor webhook payloads into the intake spool
(drained by the nightly collector). Single-user local tool: the only auth is a
shared-secret token on the webhook endpoint.

Run: uvicorn api.server:app --host 127.0.0.1 --port 8077
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import Body, FastAPI, HTTPException, Query

from analytics import store
from collector import paths
from collector.models import load_jsonl

app = FastAPI(title="hw-dashboard", version="0.1.0")

WEBHOOK_TOKEN_ENV = "HW_DASHBOARD_WEBHOOK_TOKEN"


def _read_json(path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{path.name} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _list_json(directory):
    if not directory.exists():
        return []
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(directory.glob("*.json"))
    ]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/profile")
def profile():
    return _read_json(paths.MACHINE_PROFILE)


@app.get("/api/components")
def components():
    return _list_json(paths.COMPONENTS_DIR)


@app.get("/api/components/{component_id}")
def component(component_id: str):
    return _read_json(paths.COMPONENTS_DIR / f"{component_id}.json")


@app.get("/api/skus/{sku_id}")
def sku(sku_id: str):
    return _read_json(paths.SKUS_DIR / f"{sku_id}.json")


@app.get("/api/skus/{sku_id}/series")
def series(sku_id: str):
    """Merged first-party + seed price points, chronologically sorted."""
    rows = [
        *load_jsonl(paths.seed_path(sku_id)),
        *load_jsonl(paths.series_path(sku_id)),
    ]
    return sorted(rows, key=lambda r: r.get("capture_date", ""))


@app.get("/api/analytics")
def analytics_index():
    if not paths.ANALYTICS_INDEX.exists():
        return []
    return json.loads(paths.ANALYTICS_INDEX.read_text(encoding="utf-8"))


@app.get("/api/analytics/{sku_id}")
def analytics_one(sku_id: str):
    return _read_json(paths.analytics_path(sku_id))


@app.get("/api/recommendation")
def recommendation():
    return _read_json(paths.RECOMMENDATION)


@app.post("/api/analytics/recompute")
def recompute(payload: dict = Body(default={})):
    sku_id = payload.get("sku_id")
    if sku_id:
        return store.recompute_one(sku_id)
    return store.recompute_all()


@app.post("/api/webhook/firecrawl")
def firecrawl_webhook(payload: dict = Body(...), token: str = Query(default="")):
    expected = os.environ.get(WEBHOOK_TOKEN_ENV)
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="invalid or missing token")
    paths.INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    spool = paths.INTAKE_DIR / f"{uuid.uuid4().hex}.json"
    spool.write_text(json.dumps(payload), encoding="utf-8")
    return {"spooled": spool.name}
