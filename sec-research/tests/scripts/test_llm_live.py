from __future__ import annotations
import json
import os
from pathlib import Path
import pytest

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "llm"


@pytest.mark.skipif(os.environ.get("LLM_LIVE") != "1",
                    reason="live LLM test; set LLM_LIVE=1 (and a provider key/server)")
def test_live_hypothesis_roundtrip():
    from llm.client import select_client
    from llm.schema import load_schema, wrapper_schema, validate_hypothesis
    from llm.prompt import build_prompt
    from llm.playbook import load_playbooks, select_playbooks
    recon = json.loads((FIX / "recon_item_lodash.json").read_text("utf-8"))
    pbs = select_playbooks(recon, load_playbooks())
    assert pbs, "seed playbook must select for the fixture"
    system, messages = build_prompt(recon, pbs)
    client = select_client()  # honors SECRESEARCH_LLM_PROVIDER
    resp = client.complete_json(system=system, messages=messages,
                                schema=wrapper_schema(load_schema()))
    payload = json.loads(resp.text)
    assert "hypotheses" in payload
