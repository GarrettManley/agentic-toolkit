import pytest
import yaml


def _valid_min_scope(slug):
    return {
        "program_slug": slug,
        "venue": "huntr",
        "loaded_at": "2026-06-20T00:00:00Z",
        "loaded_from": "https://huntr.com/repos/acme/acme",
        "in_scope": [{"asset_type": "package", "identifier": "acme", "ecosystem": "npm"}],
        "out_of_scope": [],
        "rules": {"ai_assistance_allowed": True},
        "submission": {"protocol": "manual-form"},
    }


def test_write_scope_creates_dir_disclosed_and_invalidates_cache(tmp_programs):
    from lib import scope_io, scope_match
    data = _valid_min_scope("acme-pkg")
    path = scope_io.write_scope("acme-pkg", data)
    assert path == tmp_programs / "acme-pkg" / "scope.yaml"
    assert (tmp_programs / "acme-pkg" / "disclosed").is_dir()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert loaded == data
    assert list(loaded.keys())[0] == "program_slug"  # sort_keys=False preserved order
    ok, prog = scope_match.is_in_scope("package", "acme")
    assert ok and prog == "acme-pkg"  # cache was invalidated -> new scope visible


def test_write_scope_refuses_existing_without_force(tmp_programs):
    from lib import scope_io
    scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"))
    with pytest.raises(FileExistsError):
        scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"))


def test_write_scope_force_overwrites(tmp_programs):
    from lib import scope_io
    scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"))
    d2 = _valid_min_scope("acme-pkg")
    d2["display_name"] = "changed"
    scope_io.write_scope("acme-pkg", d2, force=True)
    loaded = yaml.safe_load((tmp_programs / "acme-pkg" / "scope.yaml").read_text(encoding="utf-8"))
    assert loaded["display_name"] == "changed"


def test_write_draft_does_not_invalidate_cache_or_create_scope_yaml(tmp_programs):
    from lib import scope_io, scope_match
    p = scope_io.write_draft("bad-prog", {"program_slug": "bad-prog", "in_scope": [
        {"asset_type": "package", "identifier": "ghost"}]})
    assert p.name == "scope.draft.yaml"
    assert not (p.parent / "scope.yaml").exists()
    ok, _ = scope_match.is_in_scope("package", "ghost")
    assert ok is False  # draft is invisible to the scope matcher


def test_scaffold_aux_writes_notes_and_targets(tmp_programs):
    from lib import scope_io
    scope_io.write_scope("acme-pkg", _valid_min_scope("acme-pkg"), scaffold_aux=True)
    assert (tmp_programs / "acme-pkg" / "notes.md").exists()
    assert (tmp_programs / "acme-pkg" / "targets.txt").exists()
