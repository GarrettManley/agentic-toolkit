"""Collector tests — all offline (fixture HTML + intake spool; no sockets)."""

from __future__ import annotations

import json

from collector import collect, paths, schema_io
from collector.fetch_http import fetch_url
from collector.models import PriceSnapshot
from collector.retailers import jsonld
from collector.webhook_intake import normalize


# --- JSON-LD parser ---------------------------------------------------------


def test_jsonld_parses_product_offer(fixtures_dir):
    html = (fixtures_dir / "product_jsonld.html").read_text(encoding="utf-8")
    snap = jsonld.parse(
        html,
        sku_id="rtx-4060-ti-16gb-asus",
        retailer="newegg",
        url="https://newegg.com/p",
    )
    assert snap is not None
    assert snap.price == 449.99
    assert snap.currency == "USD"
    assert snap.in_stock is True
    assert snap.source == "nightly-http"
    ok, errors = schema_io.validate("price_snapshot", snap.to_dict())
    assert ok, errors


def test_jsonld_returns_none_on_layout_change(fixtures_dir):
    html = (fixtures_dir / "no_price.html").read_text(encoding="utf-8")
    assert jsonld.parse(html, sku_id="x", retailer="newegg") is None


# --- fetch seam -------------------------------------------------------------


def test_fetch_url_from_fixture_opens_no_socket(fixtures_dir):
    body = fetch_url("https://example.com", from_fixture=fixtures_dir / "no_price.html")
    assert "Mystery Card" in body


# --- idempotent append ------------------------------------------------------


def _snap(retailer="newegg", date="2026-06-22", price=449.99):
    return PriceSnapshot(
        sku_id="rtx-4060-ti-16gb-asus",
        captured_at="2026-06-22T09:00:00Z",
        capture_date=date,
        price=price,
        currency="USD",
        retailer=retailer,
        source="nightly-http",
    )


def test_append_is_idempotent_per_day_and_retailer(tmp_data):
    assert collect.append_snapshot(_snap()) is True
    assert (
        collect.append_snapshot(_snap(price=399.99)) is False
    )  # same (sku,date,retailer)
    assert collect.append_snapshot(_snap(retailer="bestbuy")) is True  # diff retailer
    assert collect.append_snapshot(_snap(date="2026-06-23")) is True  # diff day
    rows = [
        json.loads(line)
        for line in paths.series_path("rtx-4060-ti-16gb-asus")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 3


# --- webhook normalize ------------------------------------------------------


def test_webhook_normalize_valid():
    snap = normalize(
        {
            "sku_id": "rtx-4060-ti-16gb-asus",
            "price": "$429.99",
            "retailer": "newegg",
            "monitor_id": "mon_1",
        }
    )
    assert snap is not None
    assert snap.price == 429.99
    assert snap.source == "firecrawl-monitor"


def test_webhook_normalize_missing_fields_returns_none():
    assert normalize({"price": 100}) is None


# --- run_collect end-to-end via intake spool (offline) ----------------------


def test_run_collect_drains_intake_and_is_idempotent(tmp_data):
    payload = {
        "sku_id": "rtx-4060-ti-16gb-asus",
        "price": 419.99,
        "retailer": "newegg",
        "capture_date": "2026-06-22",
        "captured_at": "2026-06-22T09:00:00Z",
    }
    (paths.INTAKE_DIR / "evt1.json").write_text(json.dumps(payload), encoding="utf-8")

    rec = collect.run_collect()
    assert rec["appended"] == 1
    assert rec["attempted"] == 1
    assert paths.RUN_LOG.exists()

    # intake file consumed; re-running with the same key (re-spooled) is a no-op append
    (paths.INTAKE_DIR / "evt2.json").write_text(json.dumps(payload), encoding="utf-8")
    rec2 = collect.run_collect()
    assert rec2["appended"] == 0  # duplicate (sku, date, retailer)
    log_lines = paths.RUN_LOG.read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 2
