"""Stage 6 finding-template registry (mirrors verify/templated.TEMPLATE_REGISTRY)."""
from __future__ import annotations
from typing import Callable
from scripts.verify.model import Verdict
from scripts.draft.model import FindingDoc
from scripts.draft.errors import IncompleteVerdict  # re-export for the public registry API
from scripts.draft.templates.dependency_cve__npm import build as _build_dep_cve_npm

__all__ = ["FINDING_TEMPLATE_REGISTRY", "select_finding_template", "ecosystem_of", "IncompleteVerdict"]

FINDING_TEMPLATE_REGISTRY: dict[tuple[str, str], Callable[[Verdict, list], FindingDoc]] = {
    ("dependency-cve", "npm"): _build_dep_cve_npm,
}


def ecosystem_of(verdict: Verdict) -> str:
    if verdict.template_id and ":" in verdict.template_id:
        return verdict.template_id.split(":", 1)[0]
    return ""


def select_finding_template(vuln_class: str, ecosystem: str):
    return FINDING_TEMPLATE_REGISTRY.get((vuln_class, ecosystem))
