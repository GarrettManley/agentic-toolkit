"""Dataclasses + helpers shared across the collector.

PriceSnapshot is the in-memory form of one price_snapshot.schema.json row;
`to_dict` produces the JSON written to the series. FetchResult mirrors the
sec-research fetch-result idiom (ok / id / payload / warnings)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Denver")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_today() -> str:
    """Local (Mountain Time) calendar date — the per-day idempotency key."""
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


@dataclass(frozen=True)
class PriceSnapshot:
    sku_id: str
    captured_at: str
    capture_date: str
    price: float
    currency: str
    retailer: str
    source: str
    url: str | None = None
    in_stock: bool | None = None
    condition: str = "new"
    source_detail: dict | None = None
    raw_ref: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass(frozen=True)
class FetchResult:
    ok: bool
    sku_id: str
    snapshot: PriceSnapshot | None = None
    warnings: list[str] = field(default_factory=list)


def load_jsonl(path) -> list[dict]:
    """Read a JSONL file into a list of dicts; missing file -> []."""
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
