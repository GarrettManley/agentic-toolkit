"""Stage 4c: PocStrategy Protocol, PocPlan dataclass, SeedIncomplete exception,
and select_strategy() dispatch.

Import direction: model.py imports PocPlan from here; strategy.py does NOT import
from model.py. This is the single-direction dependency that breaks any potential
cycle.

select_strategy() uses lazy imports inside each branch so test collection succeeds
even when templated.py and llm_strategy.py (Tasks 3 and 2 respectively) do not yet
exist.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# PocPlan — the materialized plan a strategy produces
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PocPlan:
    """Immutable plan produced by a PocStrategy.

    Carries everything the harness needs to drive two sandbox phases
    (install → trigger) and derive a verdict from the trigger result.
    """

    ecosystem: str
    """Package ecosystem, e.g. "npm"."""

    install_cmd: list[str]
    """Command to install the vulnerable package, e.g. ["npm", "install", "minimatch@3.0.4"]."""

    install_hosts: list[str]
    """Hosts that the install phase is allowed to reach (passed as network_allow to sandbox_run).
    Empty list means no outbound network is permitted even during install.
    """

    trigger_cmd: list[str]
    """Command to execute the exploit trigger, e.g. ["node", "trigger.js"].
    Runs airgapped (--network none) per C2.
    """

    expected_trigger_exit: int
    """Expected exit code from the trigger command on success."""

    expected_trigger_sha256: str
    """Expected sha256 of the trigger's stdout on success.
    Must be a constant-sentinel value so it is stable across runs.
    """

    files: dict[str, str]
    """Files to materialize in the workdir before install: filename → content."""

    template_id: str
    """Identifier of the template that produced this plan, e.g.
    "npm__minimatch__CVE-2022-3517". Used for tracing and verdict annotation."""


# ---------------------------------------------------------------------------
# SeedIncomplete — raised when required evidence_seed fields are missing
# ---------------------------------------------------------------------------

class SeedIncomplete(ValueError):
    """Raised by strategy.build_plan() when required evidence_seed fields are missing
    or blank.

    Caught in verify_hypotheses() and converted to a VERDICT_SKIPPED outcome.
    "skipped" is distinct from "refuted": refuted means the PoC ran and did not
    reproduce; skipped means the plan could not even be constructed.
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        field_list = ", ".join(missing) if missing else "(none)"
        super().__init__(
            f"evidence_seed is missing required fields: {field_list}"
        )


# ---------------------------------------------------------------------------
# PocStrategy Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class PocStrategy(Protocol):
    """Protocol that every PoC authoring strategy must satisfy.

    Mirrors the LLMClient Protocol shape in scripts/llm/client.py:
    a @runtime_checkable Protocol paired with a select_strategy() dispatcher.

    Duck-typing note: isinstance(obj, PocStrategy) checks for the presence of
    both supports and build_plan methods at the class level.
    """

    def supports(self, hypothesis: dict) -> bool:
        """Return True if this strategy can build a plan for the given hypothesis."""
        ...

    def build_plan(self, hypothesis: dict) -> PocPlan:
        """Build and return a PocPlan for the hypothesis.

        Raises:
            SeedIncomplete: if required evidence_seed fields are missing or blank.
        """
        ...


# ---------------------------------------------------------------------------
# select_strategy — env-driven dispatch with lazy imports
# ---------------------------------------------------------------------------

_DEFAULT_STRATEGY = "templated"
_ENV_KEY = "SECRESEARCH_POC_STRATEGY"


def select_strategy(name: str | None = None) -> PocStrategy:
    """Return the appropriate PocStrategy implementation.

    Resolution order:
    1. ``name`` argument (if provided and non-empty).
    2. ``SECRESEARCH_POC_STRATEGY`` environment variable.
    3. Default: ``"templated"``.

    The name is lowercased before dispatch.

    Uses lazy imports so that test collection succeeds even before templated.py
    and llm_strategy.py are implemented (Tasks 3 and 2).

    Raises:
        ValueError: if the resolved name is unknown.
        ImportError: if the resolved module has not been implemented yet.
    """
    resolved = (name or os.environ.get(_ENV_KEY) or _DEFAULT_STRATEGY).lower()

    if resolved == "templated":
        from verify.templated import TemplatedPocStrategy  # lazy — Task 3
        return TemplatedPocStrategy()

    if resolved == "llm":
        from verify.llm_strategy import LLMPocStrategy  # lazy — Task 2
        return LLMPocStrategy()

    raise ValueError(
        f"unknown PocStrategy name {resolved!r} "
        f"(expected 'templated' or 'llm', or set {_ENV_KEY})"
    )
