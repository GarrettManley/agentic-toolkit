"""Stage 4c: LLMPocStrategy — defined seam for LLM-backed PoC authoring.

This module exists as a deliberate, reviewable commit of the "templated now, LLM later"
hybrid-authoring decision locked during Stage 4c brainstorming (spec §1.4, §5.5).

Why this seam matters
---------------------
The templated strategy (Task 3) is restricted to exploit classes whose success collapses
to a **constant-sentinel string + exit code** — the small, fully-deterministic subset that
v1 can handle reproducibly.  Everything outside that subset (variable-output exploits,
novel vuln classes, ecosystems beyond the vertical slice) is explicitly the LLM strategy's
future territory.  Having the seam in place now means:

- ``select_strategy("llm")`` and ``SECRESEARCH_POC_STRATEGY=llm`` are valid dispatch
  paths from day one — no protocol-breaking change when the LLM implementation lands.
- The Protocol boundary (``supports`` + ``build_plan``) is already defined and tested,
  preventing interface drift between the two authoring strategies.
- Stage-6 finding-drafting and harness code can reference the strategy type uniformly.

Usage
-----
The seam is selectable but deliberately non-functional in v1::

    # Will raise NotImplementedError — intentional until LLM authoring is implemented:
    SECRESEARCH_POC_STRATEGY=llm python nightly.py

    # Programmatic dispatch (same outcome in v1):
    from verify.strategy import select_strategy
    strategy = select_strategy("llm")        # returns LLMPocStrategy()
    strategy.supports(hypothesis)            # → False (not wired)
    strategy.build_plan(hypothesis)          # → NotImplementedError

Implementation path
-------------------
When LLM-backed PoC authoring is implemented:
1. ``supports()`` should return ``True`` for hypotheses whose ``evidence_seed.vuln_class``
   is outside the constant-sentinel subset handled by the templated strategy.
2. ``build_plan()`` should call the LLM client (``scripts/llm/generate.py`` pattern) with
   a PoC-authoring prompt and materialise the response into a ``PocPlan``.
3. The ``select_strategy`` dispatcher in ``strategy.py`` requires no change.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verify.strategy import PocPlan


class LLMPocStrategy:
    """Defined seam only — LLM-backed PoC authoring for exploit classes beyond the
    constant-sentinel subset handled by the templated strategy.

    NOT wired in v1.  Select via ``SECRESEARCH_POC_STRATEGY=llm`` once the LLM
    authoring implementation is complete.  Both methods satisfy the ``PocStrategy``
    Protocol (``@runtime_checkable``) so ``isinstance(LLMPocStrategy(), PocStrategy)``
    is ``True`` and the object may be stored in any typed annotation that expects a
    ``PocStrategy`` without triggering type errors.
    """

    def supports(self, hypothesis: dict) -> bool:
        """Return False — LLM strategy is not wired in v1.

        Future: return True for hypotheses whose vuln_class is outside the
        constant-sentinel subset (i.e., not handled by TemplatedPocStrategy).
        """
        return False

    def build_plan(self, hypothesis: dict) -> "PocPlan":
        """Raise NotImplementedError — LLMPocStrategy is a defined seam only.

        Future: call the LLM client with a PoC-authoring prompt and materialise
        the response into a PocPlan (install_cmd, trigger_cmd, files, sentinels).

        Raises:
            NotImplementedError: always, until this seam is implemented.
        """
        raise NotImplementedError(
            "LLMPocStrategy is a defined seam only; wire via select_strategy('llm') "
            "after implementing LLM-backed PoC generation."
        )
