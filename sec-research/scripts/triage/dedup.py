"""Stage 5 dedup matching — pure functions over verdicts + pre-fetched advisories."""
from __future__ import annotations
import re
from scripts.verify.model import Verdict, VERDICT_VERIFIED
from scripts.recon.advisories import Advisory
from scripts.triage.model import TriageResult, DedupInfo, TRIAGE_NOVEL, TRIAGE_DUPLICATE

_CVE_RE = re.compile(r"CVE-\d{4}-\d+")

def extract_cve(verdict: Verdict) -> str | None:
    for field in (verdict.template_id or "", verdict.reason or ""):
        m = _CVE_RE.search(field)
        if m:
            return m.group(0)
    return None

def match_advisories(verdict: Verdict, advisories: list[Advisory]) -> list[str]:
    cve = extract_cve(verdict)
    if cve is None:
        return []
    hits: list[str] = []
    for a in advisories:
        if a.cve == cve or a.id == cve:
            hits.append(a.id or a.cve or cve)
    return hits

def triage_verdict(verdict: Verdict, advisories: list[Advisory], *, now: str) -> TriageResult:
    hits = match_advisories(verdict, advisories)
    checked = [a.cve or a.id for a in advisories if (a.cve or a.id)]
    source = "recon-osv" if advisories else "none"
    is_novel = not hits
    return TriageResult(
        verdict=verdict, is_novel=is_novel,
        dedup=DedupInfo(checked_against=checked, duplicates_found=hits, checked_at=now, source=source),
        triage_status=TRIAGE_NOVEL if is_novel else TRIAGE_DUPLICATE,
    )

def triage_verdicts(verdicts: list[Verdict], advisories: list[Advisory], *, now: str) -> list[TriageResult]:
    return [triage_verdict(v, advisories, now=now) for v in verdicts if v.verdict == VERDICT_VERIFIED]
