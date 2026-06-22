"""Advisory correlation over a dependency closure.

OSV batch query is the correlation engine (aggregates GHSA/PyPA/RustSec/npm/Go);
per-id detail fetches enrich severity/range/fixed. programs/<slug>/disclosed/
records are folded in as venue-known items. A source erroring is flagged (not
fatal) so the baseline records exactly where it is incomplete."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from recon import _http
from recon.deps import Dep

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{id}"
_OSV_ECOSYSTEM = {"npm": "npm", "pypi": "PyPI", "cargo": "crates.io", "rubygems": "RubyGems"}


@dataclass(frozen=True)
class Advisory:
    id: str
    cve: str | None
    source: str
    severity: str | None
    affected_range: str | None
    fixed: str | None
    package: str


def _detail_to_advisory(detail: dict, package: str) -> Advisory:
    cve = next((a for a in detail.get("aliases", []) if a.startswith("CVE-")), None)
    sev = None
    for s in detail.get("severity", []) or []:
        if s.get("score"):
            sev = s["score"]
            break
    affected_range = fixed = None
    for aff in detail.get("affected", []) or []:
        if aff.get("package", {}).get("name") in (package, None):
            for rng in aff.get("ranges", []) or []:
                for ev in rng.get("events", []) or []:
                    if "fixed" in ev:
                        fixed = ev["fixed"]
                        affected_range = f"<{fixed}"
            break
    return Advisory(id=detail.get("id", ""), cve=cve, source="osv",
                    severity=sev, affected_range=affected_range, fixed=fixed, package=package)


def _load_disclosed(disclosed_dir: Path) -> list[Advisory]:
    out: list[Advisory] = []
    if not disclosed_dir.is_dir():
        return out
    for f in sorted(disclosed_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        out.append(Advisory(id=d.get("id", f.stem), cve=d.get("cve"), source="disclosed",
                            severity=d.get("severity"), affected_range=d.get("affected_range"),
                            fixed=d.get("fixed"), package=d.get("package", "")))
    return out


def correlate(deps: list[Dep], disclosed_dir: Path, *,
              osv_batch_fixture=None, osv_detail_fixtures: dict | None = None) -> tuple[list[Advisory], list[str]]:
    errors: list[str] = []
    advisories: list[Advisory] = []

    queries = [{"package": {"name": d.name, "ecosystem": _OSV_ECOSYSTEM.get(d.ecosystem, d.ecosystem)},
                "version": d.version} for d in deps]
    try:
        batch = _http.http_post_json(_OSV_BATCH_URL, {"queries": queries},
                                     from_fixture=osv_batch_fixture)
        results = batch.get("results", [])
        for dep, res in zip(deps, results):
            for vuln in (res or {}).get("vulns", []) or []:
                vid = vuln.get("id")
                if not vid:
                    continue
                if osv_detail_fixtures is not None:
                    detail = osv_detail_fixtures.get(vid, {"id": vid})
                else:
                    detail = json.loads(_http.http_get(_OSV_VULN_URL.format(id=vid)))
                advisories.append(_detail_to_advisory(detail, dep.name))
    except _http.HttpError as e:
        errors.append(f"osv: {e}")

    advisories.extend(_load_disclosed(disclosed_dir))
    return advisories, errors
