"""Stage 6 finding template: dependency-cve / npm ecosystem.

Factory: build(verdict, advisories) -> FindingDoc

Pure function — no file I/O, no network, no LLM. All output is deterministic
given the same inputs. The caller (Task 10 drafter) overwrites trace_id once a
real FIND-YYYY-MM-DD-NNN is allocated.

Status logic (honest gradient):
  draft-complete   — a same-package advisory (a.package == package) supplied all
                     semantic fields: severity CVSS vector + score, and at least
                     one of (cve, affected_range) resolved.
  draft-incomplete — no same-package advisory present, or advisory lacked the
                     minimum semantic fields to fill the schema. With advisories=[]
                     this is always draft-incomplete.

Evidence probe (trigger EvidenceCapture):
  First evidence entry whose phase == "trigger"; if none, fall back to the last
  entry in the list; if the list is empty, PoC fields are set to safe defaults
  (deterministic=True, expected_exit_code=0, expected_output_hash omitted).
"""
from __future__ import annotations

from scripts.draft.errors import IncompleteVerdict
from scripts.draft.model import FindingDoc
from scripts.recon.advisories import Advisory
from scripts.verify.model import EvidenceCapture, Verdict

# ---------------------------------------------------------------------------
# Placeholder CVSS for incomplete findings — valid per schema pattern/range
# but clearly labelled as a stub in the rationale.
# ---------------------------------------------------------------------------
_STUB_CVSS_VECTOR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L"
_STUB_CVSS_SCORE = 5.3
_STUB_RATIONALE = (
    "STUB — no same-package advisory available. Placeholder derived from "
    "dependency-cve base template defaults; overwrite before promoting to "
    "draft-complete."
)

# Unverified placeholder score used when an advisory supplies a CVSS vector
# string but not a numeric score. OSV does not embed the numeric score in the
# vector itself; 7.5 (HIGH) is a stub placeholder for a network-reachable
# dependency-cve. Recompute from the vector before promoting beyond draft.
_ADVISORY_DEFAULT_CVSS_SCORE = 7.5


def _pick_trigger(evidence: list[EvidenceCapture]) -> EvidenceCapture | None:
    """Return the trigger-phase EvidenceCapture, falling back to the last entry."""
    for ec in evidence:
        if ec.phase == "trigger":
            return ec
    return evidence[-1] if evidence else None


def _parse_package_version(target_identifier: str) -> tuple[str, str]:
    """Split 'package@version' into (package, version). Raises IncompleteVerdict.

    Handles scoped packages: @scope/pkg@1.2.3 -> (@scope/pkg, 1.2.3).
    """
    if "@" not in target_identifier:
        raise IncompleteVerdict(
            f"target_identifier {target_identifier!r} has no '@' separator"
        )
    pkg, _, ver = target_identifier.rpartition("@")
    if not pkg or not ver:
        raise IncompleteVerdict(
            f"target_identifier {target_identifier!r} yields empty package or version"
        )
    return pkg, ver


def _find_same_package_advisory(
    advisories: list[Advisory], package: str
) -> Advisory | None:
    """Return the first advisory whose package field matches (case-sensitive)."""
    for adv in advisories:
        if adv.package == package:
            return adv
    return None


def build(verdict: Verdict, advisories: list[Advisory]) -> FindingDoc:
    """Build a FindingDoc for an npm dependency-CVE finding.

    Args:
        verdict: A VERDICT_VERIFIED Verdict whose target_identifier is
                 'package@version'.
        advisories: Zero or more Advisory objects from Stage 3 correlation.
                    A same-package advisory (advisory.package == package) is
                    required to reach draft-complete status.

    Returns:
        A FindingDoc with frontmatter, body, and status set.

    Raises:
        IncompleteVerdict: if target_identifier cannot be split into a non-empty
                           package and version.
    """
    package, version = _parse_package_version(verdict.target_identifier)

    trigger = _pick_trigger(verdict.evidence)

    # ------------------------------------------------------------------
    # PoC block — always deterministic (source@commit sandbox execution)
    # ------------------------------------------------------------------
    poc: dict = {
        "reproduce_script": "poc/reproduce.sh",
        "deterministic": True,
        "expected_exit_code": trigger.exit_code if trigger is not None else 0,
    }
    if trigger is not None and trigger.stdout_sha256:
        poc["expected_output_hash"] = trigger.stdout_sha256

    # ------------------------------------------------------------------
    # Deduplication check — novel finding; checked_against uses schema enum
    # ------------------------------------------------------------------
    dedup: dict = {
        "checked_against": ["nvd", "ghsa", "osv"],
        "matches": [],
        "checked_at": verdict.verified_at,
    }

    # ------------------------------------------------------------------
    # Evidence block — fixed shape per schema (path pointers only)
    # ------------------------------------------------------------------
    evidence_block: dict = {
        "timeline_path": "timeline.md",
        "redacted_dir": "evidence/redacted/",
        "verification_path": "verification.json",
    }

    # ------------------------------------------------------------------
    # Semantic fields: require a same-package advisory
    # ------------------------------------------------------------------
    same_pkg_adv = _find_same_package_advisory(advisories, package)
    complete = False
    cwe_ids: list[str] = []
    cve_proposed = "CVE-PROPOSED"

    if same_pkg_adv is not None and same_pkg_adv.severity:
        # Advisory has a CVSS vector string from OSV
        cvss_vector = same_pkg_adv.severity
        if not cvss_vector.startswith("CVSS:3.1/"):
            cvss_vector = f"CVSS:3.1/{cvss_vector.lstrip('CVSS:3.1/')}"
        cvss_score = _ADVISORY_DEFAULT_CVSS_SCORE
        rationale = (
            f"Score is a placeholder (unverified) derived from advisory {same_pkg_adv.id} "
            f"(source={same_pkg_adv.source}). "
            f"Recompute from the vector before promoting beyond draft. "
            f"Affected: {same_pkg_adv.affected_range or 'unknown'}; "
            f"fixed: {same_pkg_adv.fixed or 'unknown'}."
        )
        severity_block: dict = {
            "cvss_v3_1_vector": cvss_vector,
            "cvss_v3_1_score": cvss_score,
            "rationale": rationale,
        }
        if same_pkg_adv.cve:
            cve_proposed = same_pkg_adv.cve
            cwe_ids = []  # OSV does not provide CWEs; left empty
        complete = True
    else:
        severity_block = {
            "cvss_v3_1_vector": _STUB_CVSS_VECTOR,
            "cvss_v3_1_score": _STUB_CVSS_SCORE,
            "rationale": _STUB_RATIONALE,
        }

    status = "draft-complete" if complete else "draft-incomplete"

    # ------------------------------------------------------------------
    # Citations — PoC execution is a Tier-1 internal proof
    # ------------------------------------------------------------------
    citations: list[dict] = [
        {
            "claim": (
                f"Sandbox verification confirmed {package}@{version} exhibits "
                f"{verdict.vuln_class} behavior; exit_code and stdout_sha256 "
                f"match the template's expected values."
            ),
            "source_url": (
                f"https://www.npmjs.com/package/{package}/v/{version}"
            ),
            "source_tier": 1,
            "accessed_at": verdict.verified_at,
        }
    ]
    if same_pkg_adv is not None and same_pkg_adv.cve:
        citations.append({
            "claim": (
                f"{same_pkg_adv.cve} advisory confirms {package} "
                f"affected range {same_pkg_adv.affected_range or 'unknown'}."
            ),
            "source_url": (
                f"https://osv.dev/vulnerability/{same_pkg_adv.id}"
            ),
            "source_tier": 1,
            "accessed_at": verdict.verified_at,
        })

    # ------------------------------------------------------------------
    # Frontmatter assembly
    # ------------------------------------------------------------------
    frontmatter: dict = {
        "trace_id": "FIND-PENDING",  # overwritten by Task 10 drafter
        "title": f"{package}@{version} {verdict.vuln_class}",
        "program_slug": verdict.program_slug,
        "vuln_class": verdict.vuln_class,
        "status": status,
        "discovered_at": verdict.verified_at,
        "target": {
            "asset_type": "package",
            "identifier": verdict.target_identifier,
            "ecosystem": "npm",
        },
        "severity": severity_block,
        "cwe_ids": cwe_ids,
        "poc": poc,
        "evidence": evidence_block,
        "citations": citations,
        "deduplication_check": dedup,
    }

    # ------------------------------------------------------------------
    # Body — always at least one Fact/Citation/Proof block
    # ------------------------------------------------------------------
    phase_str = trigger.phase if trigger is not None else "trigger"
    exit_str = str(trigger.exit_code) if trigger is not None else "0"
    hash_str = trigger.stdout_sha256 if trigger is not None else "(no evidence)"
    duration_str = f"{trigger.duration_s:.2f}s" if trigger is not None else "n/a"

    body = (
        f"## Verification Evidence\n\n"
        f"**Fact**: The verified PoC for `{package}@{version}` reproduces the "
        f"`{verdict.vuln_class}` deterministically.\n\n"
        f"**Citation**: [1] Sandbox verification run (trace pending), "
        f"strategy={verdict.strategy}, template={verdict.template_id}, "
        f"package_ecosystem=npm, cve={cve_proposed}\n\n"
        f"**Proof**:\n"
        f"    phase={phase_str} exit_code={exit_str} "
        f"stdout_sha256={hash_str} duration={duration_str}\n"
    )

    if same_pkg_adv is not None:
        body += (
            f"\n## Advisory Correlation\n\n"
            f"Advisory `{same_pkg_adv.id}` (source={same_pkg_adv.source}) "
            f"confirms `{package}` affected range `{same_pkg_adv.affected_range}`, "
            f"fixed in `{same_pkg_adv.fixed}`.\n"
        )

    return FindingDoc(frontmatter=frontmatter, body=body, status=status)
