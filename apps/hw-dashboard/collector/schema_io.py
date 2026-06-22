"""Thin wrapper around jsonschema for validating hw-dashboard data against
schema/<name>.schema.json. Mirrors the sec-research house validator: one schema
at a time, no external registry (schemas are self-contained via local $defs)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from collector import paths


@lru_cache(maxsize=None)
def _load_schema(name: str) -> dict[str, Any]:
    path = paths.SCHEMA_DIR / f"{name}.schema.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(name: str, data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate data against schema/<name>.schema.json. Returns (ok, errors)."""
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(_load_schema(name))
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return True, []
    return False, [
        f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in errors
    ]
