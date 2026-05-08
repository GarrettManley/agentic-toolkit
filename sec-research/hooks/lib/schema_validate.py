"""Thin wrapper around jsonschema for validating finding/program/etc. data.

Tries to use `jsonschema` package; raises ImportError with helpful message if missing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import SCHEMA_DIR


def _load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.schema.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(name: str, data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate data against schema/<name>.schema.json. Returns (ok, errors)."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return False, [
            "jsonschema package not installed. Run: pip install jsonschema (or uv add jsonschema)"
        ]

    schema = _load_schema(name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return True, []
    msgs = [f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
    return False, msgs


def validate_program(data: dict[str, Any]) -> tuple[bool, list[str]]:
    return validate("program", data)


def validate_finding_frontmatter(data: dict[str, Any]) -> tuple[bool, list[str]]:
    return validate("finding", data)


def validate_override_token(data: dict[str, Any]) -> tuple[bool, list[str]]:
    return validate("override", data)


def validate_submission_entry(data: dict[str, Any]) -> tuple[bool, list[str]]:
    return validate("submission", data)


def validate_evidence(vuln_class: str, data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the class-specific evidence portion against evidence.schema.json's
    matching property."""
    full_schema = _load_schema("evidence")
    class_schema = full_schema.get("properties", {}).get(vuln_class)
    if class_schema is None:
        return False, [f"unknown vuln_class: {vuln_class}"]
    try:
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(class_schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if not errors:
            return True, []
        return False, [f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
    except ImportError:
        return False, ["jsonschema not installed"]
