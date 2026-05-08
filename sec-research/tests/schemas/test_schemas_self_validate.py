"""Test that all five JSON Schemas are themselves valid JSON Schema documents."""
from __future__ import annotations

import json
import pytest
from pathlib import Path


SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schema"
SCHEMA_NAMES = ["program", "finding", "evidence", "override", "submission"]


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schema_loads(name: str) -> None:
    path = SCHEMA_DIR / f"{name}.schema.json"
    assert path.exists(), f"missing schema file: {path}"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "$schema" in data
    assert data["$schema"].startswith("https://json-schema.org/draft/")


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schema_is_valid_jsonschema(name: str) -> None:
    from jsonschema import Draft202012Validator
    path = SCHEMA_DIR / f"{name}.schema.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    Draft202012Validator.check_schema(data)
