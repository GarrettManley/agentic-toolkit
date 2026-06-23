"""Adapter: load the advisories Stage 3 recon already fetched for a program slug.

Only module coupled to recon's on-disk layout. v1 reuses this prefetch instead of
querying OSV/NVD live.

Recon persists per-program output to::

    runtime/recon/<slug>/recon.json

The file contains a JSON *list* of recon-item dicts (one per in-scope asset).
Each item carries a ``known_advisories`` list whose entries are
``dataclasses.asdict(Advisory)`` — matching the Advisory dataclass field names
exactly: id, cve, source, severity, affected_range, fixed, package.

Returns [] when no recon output exists so Stage 5 treats every verdict as novel.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.recon.advisories import Advisory

_DEFAULT_RUNTIME = Path(__file__).resolve().parents[2] / "runtime"


def load_advisories(slug: str, *, runtime_root: Path | None = None) -> list[Advisory]:
    """Load all advisories recon persisted for *slug*.

    Args:
        slug: Program slug (e.g. ``"huntr-npm-minimatch"``).
        runtime_root: Override the ``runtime/`` root (for testing).  Defaults
            to ``<repo-root>/runtime/``.

    Returns:
        Flat list of :class:`~scripts.recon.advisories.Advisory` instances
        aggregated across every asset recon recorded for the slug.  Returns
        ``[]`` if ``runtime/recon/<slug>/recon.json`` does not exist.
    """
    root = runtime_root if runtime_root is not None else _DEFAULT_RUNTIME
    recon_file = root / "recon" / slug / "recon.json"
    if not recon_file.exists():
        return []
    items: list[dict] = json.loads(recon_file.read_text(encoding="utf-8"))
    out: list[Advisory] = []
    for item in items:
        for a in item.get("known_advisories", []):
            out.append(Advisory(
                id=a.get("id", ""),
                cve=a.get("cve"),
                source=a.get("source", "osv"),
                severity=a.get("severity"),
                affected_range=a.get("affected_range"),
                fixed=a.get("fixed"),
                package=a.get("package", ""),
            ))
    return out
