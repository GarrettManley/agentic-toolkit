"""Parse and select markdown class playbooks (docs/PLAYBOOK_FORMAT.md).

A playbook is human-authored markdown with known H2 sections. The parser is
tolerant of missing sections (returns empty values) so authoring stays low
friction. select_playbooks does class-level filtering per recon item; v1's only
class is dependency-cve, gated on recon having surfaced a known advisory."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PLAYBOOKS_DIR = Path(__file__).resolve().parents[2] / "playbooks"

_H2 = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
_TRACE = re.compile(r"\*\*Trace ID\*\*:\s*(\S+)")
_UPDATED = re.compile(r"\*\*Last updated\*\*:\s*(\S+)")


@dataclass(frozen=True)
class Playbook:
    vuln_class: str
    technique: str
    trace_id: str | None
    last_updated: str | None
    when_to_look: str
    positive_signals: list[str]
    negative_signals: list[str]
    evidence_template: str
    dedup_heuristics: str
    citations: list[str]
    path: Path


def _sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    matches = list(_H2.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[m.group(1).lower()] = text[m.end():end].strip()
    return out


def _bullets(block: str) -> list[str]:
    return [ln[1:].strip() for ln in block.splitlines() if ln.strip().startswith("-")]


def parse_playbook(path: Path) -> Playbook:
    text = path.read_text(encoding="utf-8")
    sec = _sections(text)
    trace = _TRACE.search(text)
    updated = _UPDATED.search(text)
    return Playbook(
        vuln_class=path.parent.name,
        technique=path.stem,
        trace_id=trace.group(1) if trace else None,
        last_updated=updated.group(1) if updated else None,
        when_to_look=sec.get("when to look for this", ""),
        positive_signals=_bullets(sec.get("signal patterns (positive indicators)", "")),
        negative_signals=_bullets(sec.get("false-positive patterns (negative indicators)", "")),
        evidence_template=sec.get("evidence template", ""),
        dedup_heuristics=sec.get("dedup heuristics", ""),
        citations=_bullets(sec.get("citations", "")),
        path=path,
    )


def load_playbooks(root: Path | None = None) -> list[Playbook]:
    root = root or PLAYBOOKS_DIR
    if not root.exists():
        return []
    out: list[Playbook] = []
    for class_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "_meta"):
        for md in sorted(class_dir.glob("*.md")):
            out.append(parse_playbook(md))
    return out


def select_playbooks(recon_item: dict, playbooks: list[Playbook]) -> list[Playbook]:
    """Class-level filtering. v1: dependency-cve requires a recon known_advisory
    on an ecosystem package."""
    asset = recon_item.get("asset", {})
    has_advisory = bool(recon_item.get("known_advisories"))
    is_eco_package = asset.get("asset_type") == "package" and bool(asset.get("ecosystem"))
    selected: list[Playbook] = []
    for pb in playbooks:
        if pb.vuln_class == "dependency-cve" and has_advisory and is_eco_package:
            selected.append(pb)
    return selected
