import json
from pathlib import Path


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_npm_package_lock_v3_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "package-lock.json", json.dumps({
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "root", "version": "1.0.0"},
            "node_modules/lodash": {"version": "4.17.21"},
            "node_modules/ms": {"version": "2.1.3"},
        },
    }))
    c = resolve_closure(tmp_path, "npm")
    assert c.no_lockfile is False and c.lockfile == "package-lock.json"
    names = {(d.name, d.version) for d in c.deps}
    assert ("lodash", "4.17.21") in names and ("ms", "2.1.3") in names
    assert all(d.ecosystem == "npm" for d in c.deps)
    assert ("root", "1.0.0") not in names  # the "" root package is excluded
    assert c.direct == []  # v1: direct is always empty (manifest parsing is a follow-up)


def test_cargo_lock_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "Cargo.lock",
           '[[package]]\nname = "serde"\nversion = "1.0.197"\n\n'
           '[[package]]\nname = "libc"\nversion = "0.2.153"\n')
    c = resolve_closure(tmp_path, "cargo")
    names = {(d.name, d.version) for d in c.deps}
    assert ("serde", "1.0.197") in names and ("libc", "0.2.153") in names


def test_poetry_lock_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "poetry.lock",
           '[[package]]\nname = "requests"\nversion = "2.31.0"\n\n'
           '[[package]]\nname = "urllib3"\nversion = "2.2.1"\n')
    c = resolve_closure(tmp_path, "pypi")
    names = {(d.name, d.version) for d in c.deps}
    assert ("requests", "2.31.0") in names and ("urllib3", "2.2.1") in names


def test_gemfile_lock_closure(tmp_path):
    from recon.deps import resolve_closure
    _write(tmp_path / "Gemfile.lock",
           "GEM\n  remote: https://rubygems.org/\n  specs:\n"
           "    rack (3.0.9)\n    rake (13.1.0)\n\nPLATFORMS\n  ruby\n")
    c = resolve_closure(tmp_path, "rubygems")
    names = {(d.name, d.version) for d in c.deps}
    assert ("rack", "3.0.9") in names and ("rake", "13.1.0") in names


def test_gemfile_lock_platform_gem_strips_suffix(tmp_path):
    """Platform-qualified versions like '1.16.3-x86_64-linux' must be normalised
    to '1.16.3' so they match advisory records.  Pure versions ('3.0.9') and
    pre-release dots ('1.0.0.beta1') must be left unchanged."""
    from recon.deps import resolve_closure
    _write(tmp_path / "Gemfile.lock",
           "GEM\n  remote: https://rubygems.org/\n  specs:\n"
           "    nokogiri (1.16.3-x86_64-linux)\n"
           "    rack (3.0.9)\n\nPLATFORMS\n  x86_64-linux\n")
    c = resolve_closure(tmp_path, "rubygems")
    names = {(d.name, d.version) for d in c.deps}
    assert ("nokogiri", "1.16.3") in names        # platform suffix stripped
    assert ("nokogiri", "1.16.3-x86_64-linux") not in names  # raw form absent
    assert ("rack", "3.0.9") in names             # non-platform version unchanged


def test_no_lockfile_sets_flag_and_empty_closure(tmp_path):
    from recon.deps import resolve_closure
    c = resolve_closure(tmp_path, "npm")  # empty dir
    assert c.no_lockfile is True and c.lockfile is None and c.deps == []


def test_closure_is_capped(tmp_path, monkeypatch):
    import recon.deps as deps
    monkeypatch.setattr(deps, "MAX_CLOSURE_NODES", 2)
    pkgs = {"": {"name": "root", "version": "1"}}
    for i in range(5):
        pkgs[f"node_modules/p{i}"] = {"version": f"0.0.{i}"}
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": pkgs}), encoding="utf-8")
    c = deps.resolve_closure(tmp_path, "npm")
    assert c.truncated is True and len(c.deps) == 2 and c.total_before_cap == 5


def test_infer_ecosystem_from_present_lockfile(tmp_path):
    from recon.deps import infer_ecosystem
    assert infer_ecosystem(tmp_path) is None
    (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")
    assert infer_ecosystem(tmp_path) == "cargo"


def test_infer_package_name_npm_reads_real_shape(tmp_path):
    """Real captured minimatch package.json shape — hb-322's actual live target
    (fetched via huntr, not ghsa, but the same real npm manifest bytes this GHSA
    fix must also parse correctly) — proves the reader against real bytes."""
    from recon.deps import infer_package_name
    _write(tmp_path / "package.json", json.dumps({
        "author": "Isaac Z. Schlueter <i@izs.me> (http://blog.izs.me)",
        "name": "minimatch",
        "description": "a glob matcher in javascript",
        "version": "3.0.4",
    }))
    assert infer_package_name(tmp_path, "npm") == "minimatch"


def test_infer_package_name_npm_missing_manifest_returns_none(tmp_path):
    from recon.deps import infer_package_name
    assert infer_package_name(tmp_path, "npm") is None


def test_infer_package_name_npm_malformed_json_returns_none(tmp_path):
    from recon.deps import infer_package_name
    _write(tmp_path / "package.json", "{not valid json")
    assert infer_package_name(tmp_path, "npm") is None


def test_infer_package_name_npm_missing_name_field_returns_none(tmp_path):
    from recon.deps import infer_package_name
    _write(tmp_path / "package.json", json.dumps({"version": "1.0.0"}))
    assert infer_package_name(tmp_path, "npm") is None


def test_infer_package_name_non_npm_ecosystem_returns_none(tmp_path):
    """cargo/pypi/rubygems are deferred (see plan Out of scope) — infer_package_name
    must not silently mis-handle them; it returns None, same as any unknown ecosystem."""
    from recon.deps import infer_package_name
    _write(tmp_path / "Cargo.toml", '[package]\nname = "ripgrep"\n')
    assert infer_package_name(tmp_path, "cargo") is None
    assert infer_package_name(tmp_path, "unknown-eco") is None


def test_infer_package_version_npm_reads_real_shape(tmp_path):
    from recon.deps import infer_package_version
    _write(tmp_path / "package.json", json.dumps({"name": "minimatch", "version": "3.0.4"}))
    assert infer_package_version(tmp_path, "npm") == "3.0.4"


def test_infer_package_version_npm_missing_manifest_returns_none(tmp_path):
    from recon.deps import infer_package_version
    assert infer_package_version(tmp_path, "npm") is None


def test_infer_package_version_npm_malformed_json_returns_none(tmp_path):
    from recon.deps import infer_package_version
    _write(tmp_path / "package.json", "{not valid json")
    assert infer_package_version(tmp_path, "npm") is None


def test_infer_package_version_npm_missing_version_field_returns_none(tmp_path):
    from recon.deps import infer_package_version
    _write(tmp_path / "package.json", json.dumps({"name": "minimatch"}))
    assert infer_package_version(tmp_path, "npm") is None


def test_infer_package_version_non_npm_ecosystem_returns_none(tmp_path):
    from recon.deps import infer_package_version
    assert infer_package_version(tmp_path, "cargo") is None
