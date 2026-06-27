"""Stage 4c: LLMPocStrategy — LLM-backed differential PoC authoring for npm dependency-CVEs.

This module implements the authoring strategy using the LLM client and the
POC_AUTHOR_SCHEMA / build_poc_prompt helpers from verify.poc_prompt (Task 4).
The strategy materialises a DIFFERENTIAL PocPlan: install_cmd pins the affected
version, fixed_install_cmd pins the fixed version, and both sha256 digests are
computed from the sentinel strings returned by the LLM.

Why differential
----------------
A single-install PoC can only show that a payload fires on one version; it cannot
show that the same payload is *silenced* on the fixed version.  Running the trigger
against both installs in the same sandboxed workspace gives a definitive
confirmed/refuted pair that survives reviewer scrutiny.

Usage
-----
::

    from verify.llm_strategy import LLMPocStrategy
    strategy = LLMPocStrategy()
    if strategy.supports(hypothesis):
        plan = strategy.build_plan(hypothesis)

Repair loop::

    plan = strategy.build_plan(hypothesis, repair_context={"issue": "no-discrimination"})
"""
from __future__ import annotations

import hashlib
import json

from llm.client import LLMClient, select_client
from verify.poc_prompt import POC_AUTHOR_SCHEMA, build_poc_prompt
from verify.strategy import PocPlan, SeedIncomplete

_REQUIRED_SEED = ("package_ecosystem", "package_name", "candidate_cve_id")


class LLMPocStrategy:
    """LLM-backed differential PoC authoring for npm dependency-CVEs."""

    name: str = "llm"
    supports_repair: bool = True

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client

    def supports(self, hypothesis: dict) -> bool:
        if hypothesis.get("vuln_class") != "dependency-cve":
            return False
        seed = hypothesis.get("evidence_seed") or {}
        affected = (hypothesis.get("target") or {}).get("version_or_revision") or ""
        return bool(
            (seed.get("package_ecosystem") or "").strip() == "npm"
            and (seed.get("package_name") or "").strip()
            and affected.strip()
            and (seed.get("fixed_version") or "").strip()
        )

    def build_plan(self, hypothesis: dict, repair_context: dict | None = None) -> PocPlan:
        seed = hypothesis.get("evidence_seed") or {}
        affected = (hypothesis.get("target") or {}).get("version_or_revision") or ""
        fixed = seed.get("fixed_version") or ""

        missing = [f for f in _REQUIRED_SEED if not (seed.get(f) or "").strip()]
        if not affected.strip():
            missing.append("target.version_or_revision")
        if not fixed.strip():
            missing.append("evidence_seed.fixed_version")
        if missing:
            raise SeedIncomplete(missing)

        client = self._client or select_client()
        system, messages = build_poc_prompt(hypothesis, repair_context)
        resp = client.complete_json(system=system, messages=messages, schema=POC_AUTHOR_SCHEMA)
        authored = json.loads(resp.text)

        files = dict(authored["files"])
        files.setdefault("package.json", '{\n  "name": "poc",\n  "version": "1.0.0",\n  "private": true\n}\n')

        pkg = seed["package_name"]
        cve = seed["candidate_cve_id"]
        confirmed = authored["sentinel_confirmed"]
        patched = authored["sentinel_patched"]
        return PocPlan(
            ecosystem="npm",
            install_cmd=["npm", "install", "--no-save", f"{pkg}@{affected}"],
            install_hosts=["registry.npmjs.org"],
            trigger_cmd=list(authored["trigger_cmd"]),
            expected_trigger_exit=int(authored["expected_confirmed_exit"]),
            expected_trigger_sha256=hashlib.sha256((confirmed + "\n").encode()).hexdigest(),
            files=files,
            template_id=f"llm:npm:{pkg}:{cve}",
            fixed_install_cmd=["npm", "install", "--no-save", f"{pkg}@{fixed}"],
            expected_refuted_exit=int(authored["expected_patched_exit"]),
            expected_refuted_sha256=hashlib.sha256((patched + "\n").encode()).hexdigest(),
        )
