"""Schema contract tests: every schema/*.json is itself a valid Draft 2020-12
schema, and a representative valid/invalid instance validates as expected."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from collector import paths, schema_io

SCHEMA_FILES = sorted(paths.SCHEMA_DIR.glob("*.schema.json"))
SCHEMA_NAMES = [p.name[: -len(".schema.json")] for p in SCHEMA_FILES]


def test_schema_dir_is_populated():
    assert SCHEMA_NAMES, "no schemas found"
    expected = {
        "component",
        "sku",
        "price_snapshot",
        "seed_price_point",
        "analytics",
        "recommendation",
    }
    assert expected <= set(SCHEMA_NAMES)


@pytest.mark.parametrize("schema_file", SCHEMA_FILES, ids=SCHEMA_NAMES)
def test_each_schema_is_valid(schema_file: Path):
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(
        schema
    )  # raises if the schema itself is malformed


def test_valid_price_snapshot_passes():
    ok, errors = schema_io.validate(
        "price_snapshot",
        {
            "sku_id": "rtx-4060-ti-16gb-asus",
            "captured_at": "2026-06-22T09:00:00Z",
            "capture_date": "2026-06-22",
            "price": 449.99,
            "currency": "USD",
            "retailer": "newegg",
            "source": "nightly-http",
        },
    )
    assert ok, errors


def test_invalid_price_snapshot_fails():
    ok, errors = schema_io.validate(
        "price_snapshot",
        {
            "sku_id": "Bad SKU With Spaces",
            "capture_date": "2026-06-22",
            "price": -5,
            "currency": "USD",
            "retailer": "newegg",
            "source": "carrier-pigeon",  # not in enum
        },
    )
    assert not ok
    assert errors


def test_tier3_citation_requires_corroborator():
    ok, _ = schema_io.validate(
        "component",
        {
            "component_id": "rtx-4060-ti-16gb",
            "category": "gpu",
            "name": "RTX 4060 Ti 16GB",
            "manufacturer": "NVIDIA",
            "created_at": "2026-06-22T09:00:00Z",
            "source_citations": [
                {
                    "url": "https://blog.example.com/p",
                    "tier": 3,
                    "claim": "has 16GB VRAM",
                }
            ],
        },
    )
    assert not ok, "tier-3 citation without corroborator_url should fail"
