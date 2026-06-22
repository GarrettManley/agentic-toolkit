"""Generate demo price history (seed + recent first-party) for the example SKUs so
the analytics engine and dashboard have something to render before live tracking
accumulates. Idempotent: rewrites the demo series files. Not part of the nightly
path — a one-off dev/demo helper.

    uv run python scripts/seed_demo_data.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from collector import paths

# (sku_id, seed_start_price, recent_prices) — recent_prices are the last N daily
# first-party captures ending today; seed is monthly history before that.
DEMO = {
    "rtx-4060-ti-16gb-asus": (
        519.0,
        [469.99, 459.99, 449.99, 449.99, 439.99, 449.99, 429.99],
    ),
    "ddr5-64gb-6000-cl30-gskill": (
        239.0,
        [214.99, 209.99, 199.99, 204.99, 199.99, 194.99, 189.99],
    ),
}


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def main() -> None:
    today = date.today()
    for sku_id, (seed_start, recent) in DEMO.items():
        # 6 monthly seed points trending down from seed_start, ending ~30d before today
        seed_rows = []
        for i in range(6):
            d = today - timedelta(days=210 - i * 30)
            price = round(seed_start - i * (seed_start - recent[0]) / 6, 2)
            seed_rows.append(
                {
                    "sku_id": sku_id,
                    "capture_date": d.isoformat(),
                    "price": price,
                    "currency": "USD",
                    "retailer": "pcpartpicker-history",
                    "source": "seed",
                    "seed_provenance": {
                        "source_name": "PCPartPicker price history",
                        "granularity": "monthly",
                        "source_url": "https://pcpartpicker.com/product/",
                        "note": "demo seed",
                    },
                }
            )
        _write_jsonl(paths.seed_path(sku_id), seed_rows)

        # recent daily first-party captures ending today
        n = len(recent)
        series_rows = []
        for i, price in enumerate(recent):
            d = today - timedelta(days=n - 1 - i)
            series_rows.append(
                {
                    "sku_id": sku_id,
                    "capture_date": d.isoformat(),
                    "captured_at": f"{d.isoformat()}T09:00:00Z",
                    "price": price,
                    "currency": "USD",
                    "retailer": "newegg",
                    "in_stock": True,
                    "source": "nightly-http",
                    "source_detail": {"parser_version": "jsonld@1"},
                }
            )
        _write_jsonl(paths.series_path(sku_id), series_rows)
        print(
            f"seeded {sku_id}: {len(seed_rows)} seed + {len(series_rows)} first-party"
        )


if __name__ == "__main__":
    main()
