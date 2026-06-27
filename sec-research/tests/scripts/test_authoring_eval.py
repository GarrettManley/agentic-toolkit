"""Offline tests for the hb-0vq authoring-reliability harness.

The scorers must be trustworthy without a GPU or Docker: a fake LLM client
feeds scripted JSON, and (for Track B) an injected runner stands in for the
sandbox. This proves the *measurement* code before any live model is run.
"""
import json
from pathlib import Path

from llm.client import ChatResponse
from eval.authoring_eval import score_track_a, score_track_b, seed_complete

FIX = Path(__file__).parents[1] / "fixtures" / "llm"


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _diff_runner(confirmed="VULN\n", patched="SAFE\n"):
    """A subprocess.run stand-in driving a clean differential 'verified':
    affected trigger emits the confirmed sentinel, fixed trigger emits the patched
    one. Affected vs fixed is told apart by the workdir suffix in the -v mount."""
    def runner(argv, **_kw):
        joined = " ".join(argv)
        if "trigger.js" not in joined:        # install phase
            return _FakeCompleted(returncode=0)
        if "-fixed" in joined:
            return _FakeCompleted(returncode=0, stdout=patched)
        return _FakeCompleted(returncode=0, stdout=confirmed)
    return runner


_GOOD_POC = {
    "files": {"trigger.js": "process.stdout.write('VULN\\n')"},
    "trigger_cmd": ["node", "trigger.js"],
    "sentinel_confirmed": "VULN", "expected_confirmed_exit": 0,
    "sentinel_patched": "SAFE", "expected_patched_exit": 0,
    "reasoning": "differential ReDoS probe",
}


class _FakeClient:
    """Returns a scripted sequence of raw JSON strings, one per complete_json call."""

    provider = "fake"

    def __init__(self, payloads):
        self._p = list(payloads)
        self.model = "fake-model"

    def complete_json(self, **_):
        return ChatResponse(self._p.pop(0), "fake", "fake-model", "stop", None)


def _wrap(items):
    return json.dumps({"hypotheses": items})


def _model_output(**overrides):
    """A model-output-shaped dependency-cve hypothesis: conforms to model_item_schema
    (NO server-stamped fields), so it is a faithful sample of what the LLM emits."""
    out = {
        "program_slug": "huntr-npm-minimatch",
        "target": {"asset_type": "package", "identifier": "minimatch",
                   "version_or_revision": "3.0.4", "ecosystem": "npm"},
        "vuln_class": "dependency-cve",
        "source_playbook": {"vuln_class": "dependency-cve", "technique": "known-cve-differential"},
        "rationale": "minimatch <3.0.5 is vulnerable to ReDoS via crafted glob patterns.",
        "confidence": 0.7,
        "signals_matched": ["known_advisory:CVE-2022-3517"],
        "evidence_seed": {
            "package_ecosystem": "npm", "package_name": "minimatch",
            "affected_versions_range": "<3.0.5", "candidate_cve_id": "CVE-2022-3517",
        },
    }
    out.update(overrides)
    return out


def test_seed_complete_requires_npm_seed_and_target():
    good = json.loads((FIX / "hypothesis_minimatch.json").read_text(encoding="utf-8"))
    assert seed_complete(good) is True
    bad = json.loads((FIX / "hypothesis_minimatch.json").read_text(encoding="utf-8"))
    bad["evidence_seed"] = {}
    assert seed_complete(bad) is False


def test_seed_complete_rejects_non_dependency_cve():
    good = _model_output(vuln_class="rce")
    assert seed_complete(good) is False


def test_score_track_a_buckets_good_and_empty_seed():
    recon = json.loads((FIX / "recon_item_minimatch.json").read_text(encoding="utf-8"))
    good = _model_output()
    empty = _model_output(evidence_seed={})
    client = _FakeClient([_wrap([good]), _wrap([empty])])
    res = score_track_a(recon, client=client, trials=2)
    assert res.complete == 1
    assert res.empty_seed == 1
    assert res.rate == 0.5


def test_score_track_a_counts_parse_errors():
    recon = json.loads((FIX / "recon_item_minimatch.json").read_text(encoding="utf-8"))
    client = _FakeClient(["not json at all"])
    res = score_track_a(recon, client=client, trials=1)
    assert res.parse_errors == 1
    assert res.complete == 0
    assert res.rate == 0.0


def test_score_track_b_counts_verified(monkeypatch):
    import sandbox.runner as r
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    hyp = json.loads((FIX / "hypothesis_minimatch.json").read_text(encoding="utf-8"))
    client = _FakeClient([json.dumps(_GOOD_POC)])
    res = score_track_b(hyp, client=client, trials=1, runner=_diff_runner())
    assert res.verified == 1
    assert res.rate == 1.0


def test_score_track_b_counts_refuted_when_affected_silenced(monkeypatch):
    import sandbox.runner as r
    monkeypatch.setattr(r, "check_http", lambda url, *, bootstrap_hosts: None)

    hyp = json.loads((FIX / "hypothesis_minimatch.json").read_text(encoding="utf-8"))
    client = _FakeClient([json.dumps(_GOOD_POC)])
    # Affected emits the PATCHED sentinel -> affected-not-vulnerable -> refuted.
    res = score_track_b(hyp, client=client, trials=1,
                        runner=_diff_runner(confirmed="SAFE\n", patched="SAFE\n"))
    assert res.refuted == 1
    assert res.verified == 0
