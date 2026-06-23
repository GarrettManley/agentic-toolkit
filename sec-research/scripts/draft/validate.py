"""Stage 6 finding self-validator.

Validates a FindingDoc before Task 10 writes it to disk. Three checks:
  (a) every top-level required key from schema/finding.schema.json is present
      in doc.frontmatter;
  (b) doc.frontmatter["status"] is one of the schema's status enum values;
  (c) if status == "draft-complete": enforce the PoT-2 evidence discipline —
      every Fact:/Claim: line in doc.body must be followed within ~12 lines by
      both a Citation: and a Proof: line. status == "draft-incomplete" relaxes
      this check (EVIDENCE_DISCIPLINE "OK to leave unfinished").

Schema is loaded once at module level so the validator tracks schema changes
without hardcoding required-keys or status enum values here.

PoT-2 regex + window reused verbatim from hooks/posttooluse.py
(check_pot2_citation_discipline, lines 90-108) so the validator and the live
hook agree on what constitutes a disciplined fact.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.draft.model import FindingDoc

# ---------------------------------------------------------------------------
# Schema — loaded once at module init. Path resolves from sec-research/ root:
#   scripts/draft/validate.py  ->  ../..  ->  sec-research/  ->  schema/
# ---------------------------------------------------------------------------
_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schema" / "finding.schema.json"
_schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

# Required top-level keys (from schema["required"])
_REQUIRED_KEYS: list[str] = _schema["required"]

# Valid status enum values (from schema["properties"]["status"]["enum"])
_STATUS_ENUM: list[str] = _schema["properties"]["status"]["enum"]


# ---------------------------------------------------------------------------
# PoT-2 patterns — copied from hooks/posttooluse.py lines 90-108
# (check_pot2_citation_discipline) so validator and live hook agree exactly.
# Window size = 12 lines (matches hook's i:i+12 slice).
# ---------------------------------------------------------------------------
_POT2_FACT_CLAIM_RE_1 = re.compile(
    r"^\s*\*\*?(Fact|Claim)\*\*?\s*:", re.IGNORECASE
)
_POT2_FACT_CLAIM_RE_2 = re.compile(
    r"^\s*(Fact|Claim)\s*:", re.IGNORECASE
)
_POT2_CITATION_RE = re.compile(
    r"^\s*\*?\*?Citation\*?\*?\s*:", re.MULTILINE | re.IGNORECASE
)
_POT2_PROOF_RE = re.compile(
    r"^\s*\*?\*?Proof\*?\*?\s*:", re.MULTILINE | re.IGNORECASE
)
_POT2_WINDOW = 12  # number of lines to scan after each Fact/Claim line


class FindingInvalid(Exception):
    """Raised when a FindingDoc fails self-validation."""


def validate_finding(doc: FindingDoc) -> None:
    """Validate a FindingDoc against schema required-keys, status enum, and PoT-2.

    Args:
        doc: The FindingDoc to validate.

    Raises:
        FindingInvalid: with a descriptive message naming the first violation.
    """
    _check_required_keys(doc)
    _check_status_enum(doc)
    if doc.status == "draft-complete":
        _check_pot2_evidence_discipline(doc)


def _check_required_keys(doc: FindingDoc) -> None:
    """(a) All schema-required top-level keys must be present in frontmatter."""
    missing = [k for k in _REQUIRED_KEYS if k not in doc.frontmatter]
    if missing:
        raise FindingInvalid(
            f"FindingDoc is missing required frontmatter key(s): {missing!r}. "
            f"Required by schema/finding.schema.json: {_REQUIRED_KEYS!r}"
        )


def _check_status_enum(doc: FindingDoc) -> None:
    """(b) status must be a member of the schema's status enum."""
    status = doc.frontmatter.get("status", doc.status)
    if status not in _STATUS_ENUM:
        raise FindingInvalid(
            f"FindingDoc status {status!r} is not a valid schema enum value. "
            f"Valid values: {_STATUS_ENUM!r}"
        )


def _check_pot2_evidence_discipline(doc: FindingDoc) -> None:
    """(c) PoT-2 evidence discipline: each Fact/Claim must have Citation+Proof within 12 lines.

    Only enforced when status == "draft-complete". Mirrors the logic in
    hooks/posttooluse.py check_pot2_citation_discipline (lines 90-108).
    """
    lines = doc.body.splitlines()
    for i, line in enumerate(lines):
        is_fact_claim = (
            _POT2_FACT_CLAIM_RE_1.match(line)
            or _POT2_FACT_CLAIM_RE_2.match(line)
        )
        if not is_fact_claim:
            continue
        window = "\n".join(lines[i : i + _POT2_WINDOW])
        if not _POT2_CITATION_RE.search(window):
            raise FindingInvalid(
                f"PoT-2 violation at body line {i + 1}: Fact/Claim line "
                f"{line.strip()!r} lacks a 'Citation:' within {_POT2_WINDOW} lines. "
                f"Every claim must have a Tier-1 citation (PoT-2 rule)."
            )
        if not _POT2_PROOF_RE.search(window):
            raise FindingInvalid(
                f"PoT-2 violation at body line {i + 1}: Fact/Claim line "
                f"{line.strip()!r} lacks a 'Proof:' within {_POT2_WINDOW} lines "
                f"(cite source code snippet, command output, or HTTP trace)."
            )
