"""Stage 6 draft shapes + trace-id allocation."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FindingDoc:
    frontmatter: dict
    body: str
    status: str


@dataclass(frozen=True)
class DraftResult:
    trace_id: str
    path: str
    status: str


def next_trace_id(findings_root: Path, *, today: str) -> str:
    prefix = f"FIND-{today}-"
    n = sum(1 for p in findings_root.glob(f"{prefix}*") if p.is_dir()) if findings_root.exists() else 0
    return f"{prefix}{n + 1:03d}"
