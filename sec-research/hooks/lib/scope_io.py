"""Shared scope persistence for load_program.py and fetch_program.py.

write_scope writes the live programs/<slug>/scope.yaml and busts the scope cache.
write_draft writes programs/<slug>/scope.draft.yaml — deliberately a different
filename so the scope matcher (which only loads `scope.yaml`) never picks up an
unvalidated draft, and deliberately does NOT bust the cache.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from . import paths as _paths
from .scope_match import invalidate_scope_cache


def _program_dir(slug: str) -> Path:
    return _paths.PROGRAMS_DIR / slug


def write_scope(slug: str, data: dict[str, Any], *, force: bool = False,
                scaffold_aux: bool = False) -> Path:
    """Write the live scope.yaml. Raises FileExistsError if present and not force."""
    program_dir = _program_dir(slug)
    scope_path = program_dir / "scope.yaml"
    if scope_path.exists() and not force:
        raise FileExistsError(f"{scope_path} already exists; pass force=True to overwrite")
    program_dir.mkdir(parents=True, exist_ok=True)
    (program_dir / "disclosed").mkdir(exist_ok=True)
    with scope_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
    if scaffold_aux:
        notes = program_dir / "notes.md"
        if not notes.exists():
            notes.write_text(f"# Program notes: {slug}\n\n", encoding="utf-8")
        targets = program_dir / "targets.txt"
        if not targets.exists():
            targets.write_text("", encoding="utf-8")
    invalidate_scope_cache()
    return scope_path


def write_draft(slug: str, data: dict[str, Any]) -> Path:
    """Write programs/<slug>/scope.draft.yaml. Never busts the cache; never creates scope.yaml."""
    program_dir = _program_dir(slug)
    program_dir.mkdir(parents=True, exist_ok=True)
    draft_path = program_dir / "scope.draft.yaml"
    with draft_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
    return draft_path
