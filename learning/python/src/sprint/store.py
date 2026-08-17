"""Atomic JSON persistence for the ledger.

Writes go to a temporary sibling file that is then ``os.replace``-d over the
target, so a crash mid-write can never leave a half-written ledger.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from sprint.models import Ledger, ModuleRecord, SkillMastery


def load(path: Path) -> Ledger:
    """Load a ledger from ``path``; return a fresh :class:`Ledger` if absent."""
    if not path.exists():
        return Ledger()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Ledger(
        xp=raw["xp"],
        combo=raw["combo"],
        streak_days=raw["streak_days"],
        last_active=raw["last_active"],
        modules={key: ModuleRecord(**value) for key, value in raw["modules"].items()},
        skills={key: SkillMastery(**value) for key, value in raw["skills"].items()},
        achievements=list(raw["achievements"]),
    )


def save(path: Path, ledger: Ledger) -> None:
    """Persist ``ledger`` to ``path`` atomically (temp file + ``os.replace``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(ledger), indent=2), encoding="utf-8")
    os.replace(tmp, path)
