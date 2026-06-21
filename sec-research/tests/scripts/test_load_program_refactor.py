import sys
from pathlib import Path

import yaml

WS_ROOT = Path(__file__).resolve().parent.parent.parent  # sec-research/


def test_from_file_writes_scope_and_disclosed_not_notes(tmp_path, monkeypatch):
    from lib import paths, scope_match
    progs = tmp_path / "programs"; progs.mkdir()
    monkeypatch.setattr(paths, "PROGRAMS_DIR", progs)
    monkeypatch.setattr(scope_match, "PROGRAMS_DIR", progs)
    scope_match.invalidate_scope_cache()

    src = tmp_path / "scope.yaml"
    src.write_text(yaml.safe_dump({
        "program_slug": "ghsa-acme-repo", "venue": "ghsa",
        "loaded_at": "2026-06-20T00:00:00Z",
        "loaded_from": "https://github.com/acme/repo/security/advisories",
        "in_scope": [{"asset_type": "repo", "identifier": "github.com/acme/repo"}],
        "out_of_scope": [], "rules": {"ai_assistance_allowed": True},
        "submission": {"protocol": "ghsa-cli"},
    }), encoding="utf-8")

    import importlib
    lp = importlib.import_module("load_program")
    monkeypatch.setattr(sys, "argv", ["load_program.py", "--from-file", str(src)])
    rc = lp.main()
    assert rc == 0
    assert (progs / "ghsa-acme-repo" / "scope.yaml").exists()
    assert (progs / "ghsa-acme-repo" / "disclosed").is_dir()
    assert not (progs / "ghsa-acme-repo" / "notes.md").exists()  # --from-file never wrote notes.md
