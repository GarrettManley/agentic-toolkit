"""Tests for scripts/fetch_program.py — CLI dispatcher + e2e safety properties.

TDD: written before the implementation. Run with:
    python -m pytest tests/scripts/test_fetch_program_cli.py -v
from the sec-research/ directory.

Coverage:
  - Happy-path: dispatches to huntr/ghsa/ibb fetchers, writes scope.yaml via scope_io
  - Draft path: res.draft=True -> writes scope.draft.yaml, exits 1, scope.yaml absent
  - Schema-invalid path: validate_program fails -> writes scope.draft.yaml, exits 1,
    scope.yaml absent (the core safety property)
  - Fetch failure (ok=False) -> no filesystem write, exits 1
  - ScopeViolation propagated -> no filesystem write, exits 1
  - Existing-scope guard: FileExistsError without --force -> exits 1, original untouched
  - --force overwrites existing scope.yaml
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import sys

import pytest

# Ensure hooks/ is importable (conftest.py already does this, but guard for
# direct invocation outside the full suite).
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
for _p in (WORKSPACE_ROOT / "hooks", WORKSPACE_ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

FX_HUNTR = Path(__file__).resolve().parent.parent / "fixtures" / "huntr-fetch"
FX_GHSA = Path(__file__).resolve().parent.parent / "fixtures" / "ghsa-fetch"
FX_IBB = Path(__file__).resolve().parent.parent / "fixtures" / "ibb-fetch"


def _import_cli():
    """Import fetch_program fresh (avoids stale monkeypatches across tests)."""
    import importlib
    import fetch_program  # noqa: E402
    importlib.invalidate_caches()
    return fetch_program


# ---------------------------------------------------------------------------
# Happy-path dispatch tests
# ---------------------------------------------------------------------------

def test_huntr_dispatch_writes_scope_yaml(tmp_programs):
    """--venue huntr dispatches to huntr.fetch; valid result writes scope.yaml."""
    fp = _import_cli()
    rc = fp.main([
        "--venue", "huntr",
        "--identifier", "acme-org/acme-pkg",
        "--from-fixture", str(FX_HUNTR / "repo_acme-org_acme-pkg.html"),
    ])
    assert rc == 0
    assert (tmp_programs / "huntr-acme-org-acme-pkg" / "scope.yaml").exists()
    assert not (tmp_programs / "huntr-acme-org-acme-pkg" / "scope.draft.yaml").exists()


def test_ghsa_dispatch_writes_scope_yaml(tmp_programs):
    """--venue ghsa dispatches to ghsa.fetch; valid result writes scope.yaml."""
    fp = _import_cli()
    rc = fp.main([
        "--venue", "ghsa",
        "--identifier", "acme-org/acme-repo",
        "--from-fixture", str(FX_GHSA / "repos_acme-org_acme-repo.json"),
    ])
    assert rc == 0
    assert (tmp_programs / "ghsa-acme-org-acme-repo" / "scope.yaml").exists()
    assert not (tmp_programs / "ghsa-acme-org-acme-repo" / "scope.draft.yaml").exists()


def test_ibb_dispatch_writes_scope_yaml(tmp_programs):
    """--venue ibb-h1 dispatches to ibb.fetch; valid result writes scope.yaml."""
    fp = _import_cli()
    rc = fp.main([
        "--venue", "ibb-h1",
        "--identifier", "django",
        "--from-fixture", str(FX_IBB / "structured_scopes_django.json"),
    ])
    assert rc == 0
    assert (tmp_programs / "ibb-django" / "scope.yaml").exists()
    assert not (tmp_programs / "ibb-django" / "scope.draft.yaml").exists()


# ---------------------------------------------------------------------------
# Draft path: res.draft=True -> scope.draft.yaml, NOT scope.yaml
# ---------------------------------------------------------------------------

def test_draft_result_writes_draft_yaml_not_scope_yaml(tmp_programs, capsys):
    """When fetcher returns draft=True, CLI writes scope.draft.yaml and exits 1.

    The core safety property: scope.yaml must NEVER be written for a draft result.
    """
    fp = _import_cli()
    rc = fp.main([
        "--venue", "ibb-h1",
        "--identifier", "django",
        "--from-fixture", str(FX_IBB / "forbidden_403.json"),
    ])
    assert rc == 1
    # Draft file present
    assert (tmp_programs / "ibb-django" / "scope.draft.yaml").exists()
    # Live scope.yaml must NOT exist
    assert not (tmp_programs / "ibb-django" / "scope.yaml").exists()
    # Warnings surfaced to stderr
    captured = capsys.readouterr()
    assert "draft" in captured.err.lower() or "draft" in captured.out.lower()


# ---------------------------------------------------------------------------
# Schema-invalid path -> scope.draft.yaml written, scope.yaml absent
# ---------------------------------------------------------------------------

def test_schema_invalid_result_writes_draft_not_scope_yaml(tmp_programs, monkeypatch, capsys):
    """If validate_program fails, CLI must write scope.draft.yaml and exit 1.

    scope.yaml must NOT exist (the invariant that keeps the scope matcher clean).
    Mutate FETCHERS["huntr"] in-place so argparse choices remain valid.
    """
    fp = _import_cli()
    from fetchers._common import FetchResult
    bad_data = {"program_slug": "huntr-acme-org-acme-pkg"}  # missing required fields

    # setitem replaces the existing key's value; "huntr" stays in choices.
    monkeypatch.setitem(fp.FETCHERS, "huntr", MagicMock(return_value=FetchResult(
        ok=True, slug="huntr-acme-org-acme-pkg", data=bad_data, draft=False
    )))
    rc = fp.main([
        "--venue", "huntr",
        "--identifier", "acme-org/acme-pkg",
    ])

    assert rc == 1
    draft_path = tmp_programs / "huntr-acme-org-acme-pkg" / "scope.draft.yaml"
    scope_path = tmp_programs / "huntr-acme-org-acme-pkg" / "scope.yaml"
    assert draft_path.exists(), "scope.draft.yaml should exist for schema-invalid result"
    assert not scope_path.exists(), "scope.yaml must NOT exist for schema-invalid result"
    # Schema errors surfaced to stderr
    captured = capsys.readouterr()
    assert captured.err  # some error output


# ---------------------------------------------------------------------------
# Fetch failure: ok=False -> nothing written, exits 1
# ---------------------------------------------------------------------------

def test_fetch_failure_writes_nothing(tmp_programs, capsys):
    """When fetcher returns ok=False, CLI exits 1 and writes NO files."""
    fp = _import_cli()
    rc = fp.main([
        "--venue", "huntr",
        "--identifier", "acme-org/acme-pkg",
        "--from-fixture", str(FX_HUNTR / "garbage.html"),
    ])
    assert rc == 1
    # No directory should have been created under tmp_programs
    assert not list(tmp_programs.iterdir()), "no files should be written on fetch failure"
    captured = capsys.readouterr()
    assert captured.err  # error message to stderr


# ---------------------------------------------------------------------------
# ScopeViolation propagates to CLI -> nothing written, exits 1
# ---------------------------------------------------------------------------

def test_scope_violation_propagates_no_write(tmp_programs, monkeypatch, capsys):
    """ScopeViolation raised by a fetcher is caught at CLI top level; nothing written.

    Mutate FETCHERS["huntr"] in-place so argparse choices remain valid.
    """
    fp = _import_cli()
    from lib.policy import ScopeViolation

    monkeypatch.setitem(fp.FETCHERS, "huntr", MagicMock(side_effect=ScopeViolation(
        url="https://evil.example.com", host="evil.example.com",
        reason="test: not in scope"
    )))
    rc = fp.main([
        "--venue", "huntr",
        "--identifier", "acme-org/acme-pkg",
    ])

    assert rc == 1
    assert not list(tmp_programs.iterdir()), "no files written on ScopeViolation"
    captured = capsys.readouterr()
    assert captured.err  # error to stderr


# ---------------------------------------------------------------------------
# Existing-scope guard: FileExistsError without --force
# ---------------------------------------------------------------------------

def test_existing_scope_blocks_without_force(tmp_programs, capsys):
    """CLI exits 1 and leaves original untouched when scope.yaml exists and no --force."""
    import yaml
    fp = _import_cli()

    # Pre-write a scope.yaml
    slug = "huntr-acme-org-acme-pkg"
    prog_dir = tmp_programs / slug
    prog_dir.mkdir()
    scope_path = prog_dir / "scope.yaml"
    original = {"program_slug": slug, "sentinel": "original"}
    scope_path.write_text(yaml.safe_dump(original), encoding="utf-8")

    rc = fp.main([
        "--venue", "huntr",
        "--identifier", "acme-org/acme-pkg",
        "--from-fixture", str(FX_HUNTR / "repo_acme-org_acme-pkg.html"),
    ])
    assert rc == 1
    # Original must be untouched
    loaded = yaml.safe_load(scope_path.read_text(encoding="utf-8"))
    assert loaded.get("sentinel") == "original"
    captured = capsys.readouterr()
    assert captured.err  # clear error message


def test_force_overwrites_existing_scope(tmp_programs):
    """--force writes new scope.yaml even if one already exists."""
    import yaml
    fp = _import_cli()

    slug = "huntr-acme-org-acme-pkg"
    prog_dir = tmp_programs / slug
    prog_dir.mkdir()
    (prog_dir / "scope.yaml").write_text(yaml.safe_dump({"sentinel": "old"}), encoding="utf-8")
    (prog_dir / "disclosed").mkdir()

    rc = fp.main([
        "--venue", "huntr",
        "--identifier", "acme-org/acme-pkg",
        "--from-fixture", str(FX_HUNTR / "repo_acme-org_acme-pkg.html"),
        "--force",
    ])
    assert rc == 0
    loaded = yaml.safe_load((tmp_programs / slug / "scope.yaml").read_text(encoding="utf-8"))
    assert loaded.get("program_slug") == slug
    assert "sentinel" not in loaded
