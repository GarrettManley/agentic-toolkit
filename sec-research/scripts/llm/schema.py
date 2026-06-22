"""Hypothesis schema loading + the model-facing schema transform.

The full schema includes server-stamped fields (hypothesis_id, recon_ref,
generated_at, generator) the LLM must NOT invent. model_item_schema() strips
them so the model only emits its judgment; the orchestrator stamps the rest and
validates against the full schema."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "hypothesis.schema.json"

SERVER_FIELDS: tuple[str, ...] = ("hypothesis_id", "recon_ref", "generated_at", "generator")


def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def model_item_schema(full: dict) -> dict:
    """A copy of the hypothesis schema with server-stamped fields removed."""
    item = copy.deepcopy(full)
    item.pop("$id", None)
    item.pop("$schema", None)
    for field in SERVER_FIELDS:
        item["properties"].pop(field, None)
        if field in item.get("required", []):
            item["required"].remove(field)
    return item


def wrapper_schema(full: dict) -> dict:
    """The object the model returns: {"hypotheses": [<item>, ...]}."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["hypotheses"],
        "properties": {"hypotheses": {"type": "array", "items": model_item_schema(full)}},
    }


def validate_hypothesis(obj: dict) -> tuple[bool, list[str]]:
    validator = jsonschema.Draft202012Validator(load_schema())
    errors = [e.message for e in validator.iter_errors(obj)]
    return (not errors), errors
