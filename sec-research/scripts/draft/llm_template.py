"""Closed seam for future LLM-authored finding prose (mirrors verify/llm_strategy)."""
from __future__ import annotations
from scripts.verify.model import Verdict
from scripts.draft.model import FindingDoc


class LLMFindingTemplate:
    name = "llm"

    def supports(self, verdict: Verdict) -> bool:
        return False

    def build(self, verdict: Verdict, advisories: list) -> FindingDoc:
        raise NotImplementedError("LLM finding authoring is a deferred seam (v1 deterministic-only).")
