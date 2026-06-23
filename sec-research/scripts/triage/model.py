"""Triage data shapes — output of Stage 5 dedup over verified verdicts."""
from __future__ import annotations
from dataclasses import dataclass
from scripts.verify.model import Verdict

TRIAGE_NOVEL = "novel"
TRIAGE_DUPLICATE = "duplicate"

@dataclass(frozen=True)
class DedupInfo:
    checked_against: list[str]   # advisory IDs/CVEs consulted
    duplicates_found: list[str]  # advisory IDs that matched this verdict
    checked_at: str              # ISO-8601 UTC
    source: str                  # "recon-osv" | "disclosed" | "none"

@dataclass(frozen=True)
class TriageResult:
    verdict: Verdict
    is_novel: bool
    dedup: DedupInfo
    triage_status: str           # TRIAGE_NOVEL | TRIAGE_DUPLICATE
