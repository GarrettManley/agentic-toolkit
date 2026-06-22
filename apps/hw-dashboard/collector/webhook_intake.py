"""Firecrawl-monitor webhook intake.

The local API writes each raw firecrawl-monitor change payload to the intake
spool (data/intake/*.json). `normalize` converts one payload into a PriceSnapshot
(source = firecrawl-monitor), converging on the same schema + append path as the
HTTP collector. `drain_intake` yields snapshots for every spooled payload and
removes the consumed files."""

from __future__ import annotations

import json

from collector import paths
from collector.models import PriceSnapshot, local_today, utc_now_iso


def normalize(payload: dict) -> PriceSnapshot | None:
    """Map a firecrawl-monitor change payload to a PriceSnapshot. Expects at least
    sku_id, price, retailer; returns None if those are absent."""
    sku_id = payload.get("sku_id")
    price = payload.get("price")
    retailer = payload.get("retailer")
    if not sku_id or price is None or not retailer:
        return None
    try:
        price = float(str(price).replace(",", "").replace("$", ""))
    except ValueError:
        return None
    return PriceSnapshot(
        sku_id=sku_id,
        captured_at=payload.get("captured_at") or utc_now_iso(),
        capture_date=payload.get("capture_date") or local_today(),
        price=price,
        currency=payload.get("currency", "USD"),
        retailer=retailer,
        source="firecrawl-monitor",
        url=payload.get("url"),
        in_stock=payload.get("in_stock"),
        source_detail={
            "monitor_id": payload.get("monitor_id", ""),
            "parser_version": "firecrawl-monitor@1",
        },
    )


def drain_intake(warnings: list[str]):
    """Yield a PriceSnapshot for each spooled intake payload, deleting consumed
    files. Malformed payloads are skipped with a warning."""
    if not paths.INTAKE_DIR.exists():
        return
    for p in sorted(paths.INTAKE_DIR.glob("*.json")):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warnings.append(f"intake {p.name}: not JSON")
            p.unlink()
            continue
        snap = normalize(payload)
        if snap is None:
            warnings.append(f"intake {p.name}: missing sku_id/price/retailer")
        else:
            yield snap
        p.unlink()
