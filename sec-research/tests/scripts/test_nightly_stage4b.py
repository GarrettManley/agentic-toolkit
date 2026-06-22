from __future__ import annotations
import sys
from pathlib import Path


def test_stage_hypothesize_delegates(monkeypatch):
    # Ensure scripts/ is importable the way nightly does it.
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    sys.path.insert(0, str(scripts))
    import nightly
    called = {}
    def _fake(scopes, recon, **kw):
        called["args"] = (scopes, recon)
        return [{"x": 1}]
    monkeypatch.setattr(nightly, "generate_hypotheses", _fake)
    out = nightly.stage_hypothesize({"s": {}}, [{"slug": "s"}])
    assert out == [{"x": 1}]
    assert called["args"] == ({"s": {}}, [{"slug": "s"}])
