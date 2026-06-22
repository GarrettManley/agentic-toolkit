"""Disk-backed analytics: load a SKU's merged series, recompute via the engine,
persist analytics/<sku>.json + analytics/index.json."""

from __future__ import annotations

import json

from analytics import engine
from collector import paths
from collector.models import load_jsonl


def _component_for_sku(sku_id: str) -> tuple[str | None, bool]:
    """Return (component_id, next_gen_launch_flag) by looking up the SKU's
    component record, if present."""
    sku_path = paths.SKUS_DIR / f"{sku_id}.json"
    if not sku_path.exists():
        return None, False
    component_id = json.loads(sku_path.read_text(encoding="utf-8")).get("component_id")
    if not component_id:
        return None, False
    comp_path = paths.COMPONENTS_DIR / f"{component_id}.json"
    next_gen = False
    if comp_path.exists():
        comp = json.loads(comp_path.read_text(encoding="utf-8"))
        next_gen = bool(comp.get("specs", {}).get("next_gen_launch", False))
    return component_id, next_gen


def recompute_one(sku_id: str) -> dict:
    component_id, next_gen = _component_for_sku(sku_id)
    record = engine.compute_analytics(
        sku_id=sku_id,
        component_id=component_id,
        series_rows=load_jsonl(paths.series_path(sku_id)),
        seed_rows=load_jsonl(paths.seed_path(sku_id)),
        next_gen_launch=next_gen,
    )
    paths.ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    paths.analytics_path(sku_id).write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return record


def _known_sku_ids() -> list[str]:
    ids = (
        {p.stem for p in paths.SKUS_DIR.glob("*.json")}
        if paths.SKUS_DIR.exists()
        else set()
    )
    if paths.SERIES_DIR.exists():
        ids |= {p.name[: -len(".jsonl")] for p in paths.SERIES_DIR.glob("*.jsonl")}
    return sorted(ids)


def recompute_all() -> list[dict]:
    records = [recompute_one(sku_id) for sku_id in _known_sku_ids()]
    index = [
        {
            "sku_id": r["sku_id"],
            "component_id": r.get("component_id"),
            "current_price": r["current"]["price"],
            "signal": r["recommendation"]["signal"],
            "confidence": r["recommendation"]["confidence"],
            "pct_above_low": r["historical"].get("pct_above_low"),
        }
        for r in records
    ]
    paths.ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    paths.ANALYTICS_INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return records
