"""docker-gated live integration test — Stage 4c end-to-end verification.

Proves the full verify pipeline against real containers via the deterministic
guard-presence probe (the resolved version is run; the fixed 3.0.5 rejects an
over-length pattern via its assertValidPattern guard, the affected 3.0.4 does not):
  - minimatch@3.0.4 (affected)  → verdict "verified"
  - minimatch@3.0.5 (fixed)     → verdict "refuted"

Skip conditions (both must hold to run):
  1. Docker engine reachable in WSL2 (same check as test_sandbox_runner.py).
  2. VERIFY_LIVE=1 env flag explicitly set (same pattern as test_llm_live.py).

Without VERIFY_LIVE=1 this test is always skipped — it pulls images + npm-installs,
which is too slow for the routine offline suite.
"""
from __future__ import annotations

import os
import subprocess

import pytest


def _docker_available() -> bool:
    try:
        p = subprocess.run(
            ["wsl", "-e", "docker", "info"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return p.returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(
    not _docker_available() or os.environ.get("VERIFY_LIVE") != "1",
    reason="requires docker in WSL2 + VERIFY_LIVE=1",
)
def test_minimatch_304_verified_305_refuted(tmp_path):
    """End-to-end: affected 3.0.4 is verified; fixed 3.0.5 is refuted.

    Both assertions constitute the verification proof:
      - The affected version lacks the 3.0.5 length guard → VULN_CONFIRMED.
      - The fixed version rejects the over-length pattern → PATCHED.
    """
    from verify.harness import verify_hypotheses

    # -----------------------------------------------------------------------
    # Affected version — minimatch@3.0.4
    # -----------------------------------------------------------------------
    hyp_affected = {
        "hypothesis_id": "live-test-minimatch-304",
        "program_slug": "live-test",
        "vuln_class": "dependency-cve",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "affected_versions_range": "<3.0.5",
            "candidate_cve_id": "CVE-2022-3517",
        },
        "target": {
            "asset_type": "package",
            "identifier": "minimatch",
            "ecosystem": "npm",
            "version_or_revision": "3.0.4",
        },
    }

    verdicts_affected = verify_hypotheses([hyp_affected], verdict_root=tmp_path)
    assert len(verdicts_affected) == 1
    v_affected = verdicts_affected[0]
    assert v_affected["verdict"] == "verified", (
        f"Expected minimatch@3.0.4 → verified, got {v_affected['verdict']!r}. "
        f"Reason: {v_affected.get('reason')}"
    )
    assert v_affected["verified"] is True

    # -----------------------------------------------------------------------
    # Fixed version — minimatch@3.0.5
    # -----------------------------------------------------------------------
    hyp_fixed = {
        "hypothesis_id": "live-test-minimatch-305",
        "program_slug": "live-test",
        "vuln_class": "dependency-cve",
        "evidence_seed": {
            "package_ecosystem": "npm",
            "package_name": "minimatch",
            "affected_versions_range": "<3.0.5",
            "candidate_cve_id": "CVE-2022-3517",
        },
        "target": {
            "asset_type": "package",
            "identifier": "minimatch",
            "ecosystem": "npm",
            "version_or_revision": "3.0.5",
        },
    }

    verdicts_fixed = verify_hypotheses([hyp_fixed], verdict_root=tmp_path)
    assert len(verdicts_fixed) == 1
    v_fixed = verdicts_fixed[0]
    assert v_fixed["verdict"] == "refuted", (
        f"Expected minimatch@3.0.5 → refuted, got {v_fixed['verdict']!r}. "
        f"Reason: {v_fixed.get('reason')}"
    )
    assert v_fixed["verified"] is False
