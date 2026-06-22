from __future__ import annotations
from llm.prompt import build_prompt
from llm.playbook import Playbook
from pathlib import Path


def _pb() -> Playbook:
    return Playbook("dependency-cve", "known-advisory-confirmation", "trace-pb-1", "2026-06-22",
                    "when text", ["known_advisories present"], ["overly broad range"],
                    "evidence tmpl", "dedup tmpl", ["[1] OSV"], Path("x.md"))


def _recon() -> dict:
    return {"slug": "huntr-acme",
            "asset": {"asset_type": "package", "identifier": "lodash", "ecosystem": "npm"},
            "resolved_version": "4.17.20",
            "known_advisories": [{"id": "GHSA-x", "cve": "CVE-2021-23337",
                                  "affected_range": "<4.17.21", "fixed": "4.17.21",
                                  "package": "lodash"}]}


def test_build_prompt_returns_system_and_messages():
    system, messages = build_prompt(_recon(), [_pb()])
    assert isinstance(system, str) and system
    assert messages and messages[0]["role"] == "user"


def test_prompt_includes_asset_and_signals():
    system, messages = build_prompt(_recon(), [_pb()])
    blob = system + messages[0]["content"]
    assert "lodash" in blob
    assert "CVE-2021-23337" in blob
    assert "known_advisories present" in blob  # playbook positive signal surfaced


def test_prompt_fences_untrusted_data_and_warns():
    system, messages = build_prompt(_recon(), [_pb()])
    # System prompt must tell the model fenced content is data, not instructions.
    assert "instructions" in system.lower()
    # Recon/playbook content lives inside an explicit fence marker.
    assert "BEGIN" in messages[0]["content"] and "END" in messages[0]["content"]


def test_prompt_is_deterministic():
    a = build_prompt(_recon(), [_pb()])
    b = build_prompt(_recon(), [_pb()])
    assert a == b
