"""Stage 6 drafter orchestrator.

For each novel Verdict:
  1. Select finding template from registry (skip if none).
  2. Build FindingDoc via factory (skip on IncompleteVerdict).
  3. Allocate a real trace_id and overwrite doc.frontmatter["trace_id"] BEFORE validation.
  4. Validate (skip on FindingInvalid).
  5. Write findings/<trace_id>/finding.md and evidence/redacted/sandbox_stdout.txt.
  6. Append one "draft-created" ledger event.
  7. Accumulate DraftResult.

Per-item skip-and-continue isolation mirrors verify/harness.verify_hypotheses.
Frontmatter is serialized with yaml.safe_dump (PyYAML) because scripts/verify_finding.py
and scripts/submit.py both read findings with yaml.safe_load — the same dependency is
already required by those scripts.
"""
from __future__ import annotations

import yaml

from pathlib import Path

from lib import ledger
from scripts.draft.errors import IncompleteVerdict
from scripts.draft.model import DraftResult, FindingDoc, next_trace_id
from scripts.draft.registry import ecosystem_of, select_finding_template
from scripts.draft.validate import FindingInvalid, validate_finding
from scripts.recon.advisories import Advisory
from scripts.verify.model import Verdict

_DEFAULT_FINDINGS_ROOT = Path(__file__).resolve().parents[2] / "findings"


def _serialize_finding_md(doc: FindingDoc) -> str:
    """Serialize FindingDoc to a finding.md string.

    Format: YAML frontmatter block (---\\n...\\n---\\n) + body.
    Uses yaml.safe_dump so nested dicts and citation lists round-trip correctly
    through yaml.safe_load (the format all reader scripts use).
    """
    fm_text = yaml.safe_dump(doc.frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_text}---\n{doc.body}"


def draft_findings(
    novel: list[Verdict],
    advisories: list[Advisory],
    *,
    findings_root: Path | None = None,
    today: str,
) -> list[DraftResult]:
    """Draft findings for every novel Verdict.

    Args:
        novel: Verdicts that passed triage as novel (VERDICT_VERIFIED expected).
        advisories: Advisory objects from Stage 3 recon correlation.
        findings_root: Override the default ``findings/`` root (required in tests).
        today: ISO date string YYYY-MM-DD used for trace_id allocation.

    Returns:
        List of DraftResult objects (one per successfully drafted finding).
        Skipped verdicts produce no entry.
    """
    root = findings_root if findings_root is not None else _DEFAULT_FINDINGS_ROOT

    results: list[DraftResult] = []

    for verdict in novel:
        # Step 1: resolve ecosystem + select template
        eco = ecosystem_of(verdict)
        factory = select_finding_template(verdict.vuln_class, eco)
        if factory is None:
            print(f"[draft] skipped: no template for ({verdict.vuln_class!r}, {eco!r})")
            continue

        # Step 2: build FindingDoc via factory
        try:
            doc = factory(verdict, advisories)
        except IncompleteVerdict as exc:
            print(f"[draft] skipped: IncompleteVerdict for {verdict.target_identifier!r}: {exc}")
            continue

        # Step 3: allocate real trace_id, overwrite FIND-PENDING placeholder BEFORE validation
        trace_id = next_trace_id(root, today=today)
        updated_fm = dict(doc.frontmatter)
        updated_fm["trace_id"] = trace_id
        doc = FindingDoc(frontmatter=updated_fm, body=doc.body, status=doc.status)

        # Step 4: validate — skip if invalid
        try:
            validate_finding(doc)
        except FindingInvalid as exc:
            print(f"[draft] skipped: FindingInvalid for {trace_id}: {exc}")
            continue

        # Step 5: write to disk
        finding_dir = root / trace_id
        finding_dir.mkdir(parents=True, exist_ok=True)

        finding_path = finding_dir / "finding.md"
        finding_path.write_text(_serialize_finding_md(doc), encoding="utf-8")

        evidence_dir = finding_dir / "evidence" / "redacted"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = evidence_dir / "sandbox_stdout.txt"
        lines = []
        for ev in verdict.evidence:
            lines.append(
                f"phase={ev.phase} exit_code={ev.exit_code} "
                f"stdout_sha256={ev.stdout_sha256} "
                f"timed_out={ev.timed_out} duration_s={ev.duration_s}"
            )
        stdout_path.write_text("\n".join(lines), encoding="utf-8")

        # Step 6: ledger event
        ledger.append_event(
            "draft-created",
            trace_id=trace_id,
            program_slug=verdict.program_slug,
        )

        # Step 7: accumulate result
        results.append(DraftResult(trace_id=trace_id, path=str(finding_path), status=doc.status))

    return results
