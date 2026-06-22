"""Stage 4c: TemplatedPocStrategy — registry-backed templated PoC strategy.

TEMPLATE_REGISTRY maps (ecosystem, package_name, cve_id) triples to factory
callables that each accept a hypothesis dict and return a PocPlan.  The
registry is keyed with lowercased ecosystem and exact-case package_name and
CVE id (matching the hypothesis evidence_seed values verbatim).

TemplatedPocStrategy implements the PocStrategy Protocol:
  - supports(hypothesis) → bool: True iff the (ecosystem, package, cve) triple
    from evidence_seed is registered.  Never raises on missing seed fields.
  - build_plan(hypothesis) → PocPlan: validates required evidence_seed fields,
    looks up the factory, delegates to it (which validates target.version), and
    returns the PocPlan.  Raises SeedIncomplete on missing/blank seed fields.
"""
from __future__ import annotations

from typing import Callable

from verify.strategy import PocPlan, SeedIncomplete

# ---------------------------------------------------------------------------
# Import template factories
# ---------------------------------------------------------------------------

from verify.templates.npm__minimatch__CVE_2022_3517 import (
    build as _build_minimatch_cve_2022_3517,
)

# ---------------------------------------------------------------------------
# TEMPLATE_REGISTRY
# ---------------------------------------------------------------------------

#: Maps (ecosystem, package_name, cve_id) → factory(hypothesis: dict) -> PocPlan.
#: Ecosystem is lowercased; package_name and cve_id are exact-case (match the
#: evidence_seed values produced by Stage 4b).
TEMPLATE_REGISTRY: dict[tuple[str, str, str], Callable[[dict], PocPlan]] = {
    ("npm", "minimatch", "CVE-2022-3517"): _build_minimatch_cve_2022_3517,
}

# ---------------------------------------------------------------------------
# Required evidence_seed fields for dependency-cve hypotheses
# ---------------------------------------------------------------------------

_REQUIRED_SEED_FIELDS: tuple[str, ...] = (
    "package_ecosystem",
    "package_name",
    "affected_versions_range",
    "candidate_cve_id",
)


# ---------------------------------------------------------------------------
# TemplatedPocStrategy
# ---------------------------------------------------------------------------

class TemplatedPocStrategy:
    """Registry-backed PocStrategy that delegates to pre-built exploit templates.

    supports() is designed to be safe against malformed or missing evidence_seed —
    it never raises; it returns False gracefully.

    build_plan() validates ALL required evidence_seed fields before dispatching to
    the factory.  Missing or blank fields are collected and raised together as a
    single SeedIncomplete so the harness can record all missing fields in one pass.

    If a key passes supports() but is somehow not in the registry (defensive path),
    build_plan() raises KeyError.  In normal usage supports() gates build_plan().
    """

    def supports(self, hypothesis: dict) -> bool:
        """Return True iff the hypothesis's (ecosystem, package, cve) triple is registered.

        Never raises, even if evidence_seed or individual fields are absent.
        """
        seed = hypothesis.get("evidence_seed") or {}
        ecosystem = seed.get("package_ecosystem") or ""
        package = seed.get("package_name") or ""
        cve = seed.get("candidate_cve_id") or ""
        if not (ecosystem and package and cve):
            return False
        return (ecosystem, package, cve) in TEMPLATE_REGISTRY

    def build_plan(self, hypothesis: dict) -> PocPlan:
        """Build and return a PocPlan for the hypothesis.

        Validates all required evidence_seed fields first, collecting every missing
        or blank field into a single SeedIncomplete raise.  Then looks up the factory
        and delegates (which performs its own target.version_or_revision check).

        Args:
            hypothesis: A hypothesis dict as produced by Stage 4b.

        Returns:
            A PocPlan ready for the install→trigger sandbox phases.

        Raises:
            SeedIncomplete: if any required evidence_seed field is missing or blank,
                or if the factory itself raises SeedIncomplete (e.g. missing version).
            KeyError: if the (ecosystem, package, cve) triple is not in the registry
                despite supports() returning True (defensive path; shouldn't happen).
        """
        seed = hypothesis.get("evidence_seed") or {}

        # Collect all missing/blank required fields in one pass.
        missing: list[str] = [
            field
            for field in _REQUIRED_SEED_FIELDS
            if not (seed.get(field) or "").strip()
        ]
        if missing:
            raise SeedIncomplete(missing)

        ecosystem = seed["package_ecosystem"]
        package = seed["package_name"]
        cve = seed["candidate_cve_id"]
        key = (ecosystem, package, cve)

        # Defensive lookup — KeyError here is a programming error (supports() should
        # have gated this call), not a seed-completeness issue.
        factory = TEMPLATE_REGISTRY[key]

        # Delegate to factory; it validates target.version_or_revision and may itself
        # raise SeedIncomplete — propagate directly.
        return factory(hypothesis)
