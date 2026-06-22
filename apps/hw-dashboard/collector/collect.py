"""Nightly price collector.

Reads active SKUs, fetches each tracked URL (firecrawl-monitor intake spool first,
then HTTP + JSON-LD parse), validates against price_snapshot.schema.json, and
appends idempotently to the per-SKU JSONL series. One row per (sku_id,
capture_date, retailer); re-runs the same day are no-ops, so a catch-up run after
a missed schedule is safe. Per-SKU errors land in warnings, never abort the run.

Entry point: `python -m collector.collect`.
"""

from __future__ import annotations

import json
import sys

from collector import paths, schema_io
from collector.fetch_http import FetchError, fetch_url
from collector.models import FetchResult, PriceSnapshot, load_jsonl, utc_now_iso
from collector.retailers import jsonld
from collector.webhook_intake import drain_intake


def append_snapshot(snapshot: PriceSnapshot) -> bool:
    """Append a snapshot to its SKU series unless an identical-key row exists.
    Idempotency key = (sku_id, capture_date, retailer). Returns True if written."""
    path = paths.series_path(snapshot.sku_id)
    key = (snapshot.sku_id, snapshot.capture_date, snapshot.retailer)
    for row in load_jsonl(path):
        if (row.get("sku_id"), row.get("capture_date"), row.get("retailer")) == key:
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot.to_dict()) + "\n")
    return True


def _load_active_skus() -> list[dict]:
    skus: list[dict] = []
    if not paths.SKUS_DIR.exists():
        return skus
    for p in sorted(paths.SKUS_DIR.glob("*.json")):
        sku = json.loads(p.read_text(encoding="utf-8"))
        if sku.get("active", True):
            skus.append(sku)
    return skus


def fetch_sku(sku: dict) -> list[FetchResult]:
    """Fetch every tracked URL for one SKU via HTTP + JSON-LD. Returns one
    FetchResult per tracked URL."""
    results: list[FetchResult] = []
    sku_id = sku["sku_id"]
    for entry in sku.get("tracked_urls", []):
        retailer, url = entry["retailer"], entry["url"]
        try:
            html = fetch_url(url)
        except FetchError as e:
            results.append(FetchResult(False, sku_id, warnings=[f"{retailer}: {e}"]))
            continue
        snap = jsonld.parse(html, sku_id=sku_id, retailer=retailer, url=url)
        if snap is None:
            results.append(
                FetchResult(
                    False,
                    sku_id,
                    warnings=[f"{retailer}: no price parsed (layout change?)"],
                )
            )
        else:
            results.append(FetchResult(True, sku_id, snapshot=snap))
    return results


def _validate_and_append(snapshot: PriceSnapshot, warnings: list[str]) -> int:
    ok, errors = schema_io.validate("price_snapshot", snapshot.to_dict())
    if not ok:
        warnings.append(
            f"{snapshot.sku_id}/{snapshot.retailer}: schema invalid: {errors}"
        )
        return 0
    return 1 if append_snapshot(snapshot) else 0


def run_collect() -> dict:
    """Drain the firecrawl intake spool, fetch active SKUs over HTTP, validate +
    append. Returns a run record (also appended to RUN_LOG)."""
    started = utc_now_iso()
    warnings: list[str] = []
    appended = 0
    attempted = 0

    for snap in drain_intake(warnings):  # firecrawl-monitor snapshots first
        attempted += 1
        appended += _validate_and_append(snap, warnings)

    for sku in _load_active_skus():
        for result in fetch_sku(sku):
            attempted += 1
            warnings.extend(result.warnings)
            if result.snapshot is not None:
                appended += _validate_and_append(result.snapshot, warnings)

    record = {
        "kind": "collect",
        "started_at": started,
        "finished_at": utc_now_iso(),
        "attempted": attempted,
        "appended": appended,
        "dropped": attempted - appended,
        "warnings": warnings,
    }
    paths.RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with paths.RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


def main() -> int:
    record = run_collect()
    print(
        f"[collect] attempted={record['attempted']} appended={record['appended']} "
        f"dropped={record['dropped']} warnings={len(record['warnings'])}"
    )
    for w in record["warnings"]:
        print(f"  warn: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
