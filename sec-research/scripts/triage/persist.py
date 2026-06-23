"""Persist Stage 5 triage results to runtime/triage/<slug>/triage.json.

Mirrors the pattern in scripts/verify/harness._persist: write JSON to the
runtime tree and emit a single audit ledger event summarising the run.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from lib import ledger
from scripts.triage.model import TRIAGE_NOVEL, TriageResult

_DEFAULT_RUNTIME = Path(__file__).resolve().parents[2] / "runtime"


def persist_triage(
    slug: str,
    results: list[TriageResult],
    *,
    runtime_root: Path | None = None,
) -> Path:
    """Write triage results for *slug* to runtime/triage/<slug>/triage.json.

    Args:
        slug: Program slug that identifies the triage run.
        results: Ordered list of TriageResult objects from Stage 5 dedup.
        runtime_root: Override the default ``runtime/`` root (for tests).

    Returns:
        The Path to the written ``triage.json`` file.

    Side-effect:
        Appends one ``triage-summary`` ledger event via :func:`lib.ledger.append_event`
        carrying the slug, total count, novel count, and duplicate count.
    """
    root = runtime_root if runtime_root is not None else _DEFAULT_RUNTIME
    out_dir = root / "triage" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "triage.json"
    out.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")

    novel_count = sum(1 for r in results if r.triage_status == TRIAGE_NOVEL)
    ledger.append_event(
        "triage-summary",
        slug=slug,
        total=len(results),
        novel=novel_count,
        duplicate=len(results) - novel_count,
    )

    return out
