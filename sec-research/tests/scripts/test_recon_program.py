from pathlib import Path


def _scope(slug, asset):
    assets = asset if isinstance(asset, list) else [asset]
    return {slug: {"program_slug": slug, "venue": "huntr", "in_scope": assets,
                   "out_of_scope": []}}


def test_run_recon_produces_item_per_in_scope_asset(tmp_path, monkeypatch):
    import recon_program as rp
    from recon.metadata import AssetMetadata
    from recon.deps import Closure, Dep
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.metadata, "fetch_metadata",
                        lambda ident, eco, **kw: AssetMetadata(ident, eco, latest="1.0.0",
                                                               repo_url="github.com/acme/acme"))
    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest),
                                                             commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "resolve_closure",
                        lambda src, eco: Closure(direct=[Dep("d", "1", eco)], deps=[Dep("d", "1", eco)],
                                                 lockfile="package-lock.json", total_before_cap=1))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("huntr-acme", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="2026-06-21T00:00:00Z")
    assert len(items) == 1 and items[0]["asset"]["identifier"] == "acme"
    assert (tmp_path / "huntr-acme" / "recon.json").exists()


def test_run_recon_skips_non_package_repo_assets(tmp_path, monkeypatch):
    import recon_program as rp
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))
    scopes = _scope("s", {"asset_type": "url", "identifier": "https://x.example"})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")
    assert items == []  # v1 handles only package/repo


def test_run_recon_isolates_per_asset_failure(tmp_path, monkeypatch):
    import recon_program as rp
    def boom(ident, eco, **kw):
        raise RuntimeError("registry exploded")
    monkeypatch.setattr(rp.metadata, "fetch_metadata", boom)
    monkeypatch.setattr(rp.deps, "resolve_closure",
                        lambda src, eco: __import__("recon.deps", fromlist=["Closure"]).Closure(no_lockfile=True))
    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda *a, **k: __import__("recon.clone", fromlist=["CloneResult"]).CloneResult(cloned=False, skipped_reason="x"))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))
    scopes = _scope("s", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")
    assert len(items) == 1 and any("recon_error" in f for f in items[0]["flags"])


def test_main_all_returns_zero(tmp_path, monkeypatch):
    import recon_program as rp
    monkeypatch.setattr(rp, "load_all_scopes", lambda: {})
    assert rp.main(["--all"]) == 0


def test_main_scope_violation_returns_one(tmp_path, monkeypatch):
    import recon_program as rp
    from lib.policy import ScopeViolation

    monkeypatch.setattr(rp, "load_all_scopes",
                        lambda: _scope("huntr-acme", {"asset_type": "package",
                                                       "identifier": "acme",
                                                       "ecosystem": "npm"}))
    monkeypatch.setattr(rp.metadata, "fetch_metadata",
                        lambda ident, eco, **kw: (_ for _ in ()).throw(
                            ScopeViolation(url="https://registry.npmjs.org/acme",
                                           host="registry.npmjs.org",
                                           reason="host not in scope")))
    assert rp.main(["--all"]) == 1


def test_run_recon_scope_violation_writes_nothing(tmp_path, monkeypatch):
    import pytest
    import recon_program as rp
    from lib.policy import ScopeViolation

    monkeypatch.setattr(rp.metadata, "fetch_metadata",
                        lambda ident, eco, **kw: (_ for _ in ()).throw(
                            ScopeViolation(url="https://registry.npmjs.org/acme",
                                           host="registry.npmjs.org",
                                           reason="host not in scope")))
    scopes = _scope("huntr-acme", {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"})
    with pytest.raises(ScopeViolation):
        rp.run_recon(scopes, recon_root=tmp_path, ts="t")
    assert not list(tmp_path.iterdir())


def test_run_recon_relabels_ghsa_repo_asset_when_ecosystem_and_name_resolve(tmp_path, monkeypatch):
    """The exact hb-7hf fix: a GHSA-style repo asset with no declared ecosystem, whose
    clone yields a resolvable npm manifest, becomes a package-typed recon item."""
    import recon_program as rp
    from recon.deps import Closure, Dep
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest),
                                                             commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "infer_ecosystem", lambda src: "npm")
    monkeypatch.setattr(rp.deps, "infer_package_name", lambda src, eco: "minimatch")
    monkeypatch.setattr(rp.deps, "infer_package_version", lambda src, eco: "3.0.4")
    monkeypatch.setattr(rp.deps, "resolve_closure",
                        lambda src, eco: Closure(direct=[], deps=[Dep("brace-expansion", "1.1.11", eco)],
                                                 lockfile="package-lock.json", total_before_cap=1))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("ghsa-isaacs-minimatch",
                    {"asset_type": "repo", "identifier": "github.com/isaacs/minimatch", "ecosystem": None})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="2026-07-01T00:00:00Z")

    assert len(items) == 1
    asset = items[0]["asset"]
    assert asset == {"asset_type": "package", "identifier": "minimatch", "ecosystem": "npm"}
    assert "package_identity_inferred_from_repo" in items[0]["flags"]
    # original repo provenance is preserved separately, via the repo_identifier fix (Steps 1-5)
    assert items[0]["repo"]["identifier"] == "github.com/isaacs/minimatch"
    assert items[0]["resolved_version"] == "3.0.4"


def test_run_recon_relabels_repo_asset_but_flags_unresolved_version(tmp_path, monkeypatch):
    """Package name resolves but the manifest has no parseable version — still relabel
    (package identity is independently useful) but flag the version gap distinctly, and
    leave resolved_version None (generate.py's own hypothesis-version-unresolved gate
    correctly drops any dependency-cve hypothesis with no version — this is expected,
    not a new failure mode)."""
    import recon_program as rp
    from recon.deps import Closure
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest), commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "infer_ecosystem", lambda src: "npm")
    monkeypatch.setattr(rp.deps, "infer_package_name", lambda src, eco: "minimatch")
    monkeypatch.setattr(rp.deps, "infer_package_version", lambda src, eco: None)
    monkeypatch.setattr(rp.deps, "resolve_closure", lambda src, eco: Closure(no_lockfile=True))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("ghsa-isaacs-minimatch",
                    {"asset_type": "repo", "identifier": "github.com/isaacs/minimatch", "ecosystem": None})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")

    assert len(items) == 1
    assert items[0]["asset"]["asset_type"] == "package"
    assert items[0]["resolved_version"] is None
    assert "package_version_unresolved" in items[0]["flags"]


def test_run_recon_leaves_repo_asset_unrelabeled_when_package_name_unresolved(tmp_path, monkeypatch):
    """Ecosystem infers but no manifest name is found — stay repo-typed (fail-closed),
    and say so distinctly in flags rather than silently doing nothing."""
    import recon_program as rp
    from recon.deps import Closure
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest), commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "infer_ecosystem", lambda src: "npm")
    monkeypatch.setattr(rp.deps, "infer_package_name", lambda src, eco: None)
    monkeypatch.setattr(rp.deps, "resolve_closure", lambda src, eco: Closure(no_lockfile=True))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("ghsa-x-y", {"asset_type": "repo", "identifier": "github.com/x/y", "ecosystem": None})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")

    assert len(items) == 1
    assert items[0]["asset"]["asset_type"] == "repo"
    assert "package_name_unresolved" in items[0]["flags"]


def test_run_recon_repo_asset_without_lockfile_stays_ineligible(tmp_path, monkeypatch):
    """Documented boundary (see plan Out of scope): a repo with only package.json and
    no committed package-lock.json never gets an ecosystem inferred at all, since
    deps.infer_ecosystem gates on lockfile presence — this is unchanged, pre-existing
    behavior, not a new gap this fix should silently paper over."""
    import recon_program as rp
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest), commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "infer_ecosystem", lambda src: None)  # no lockfile present
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("ghsa-no-lockfile", {"asset_type": "repo", "identifier": "github.com/a/b", "ecosystem": None})
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")

    assert len(items) == 1
    assert items[0]["asset"]["asset_type"] == "repo"
    assert "no_lockfile" in items[0]["flags"]
    assert "package_identity_inferred_from_repo" not in items[0]["flags"]
    assert "package_name_unresolved" not in items[0]["flags"]  # never attempted — no eco to try


def test_run_recon_closures_keyed_by_resolved_identifier(tmp_path, monkeypatch):
    """Regression for the planning watch-item: recon.json's recorded closure path must
    match the file actually written, even when the asset gets relabeled mid-recon.
    Follows the same convention as test_recon_item.py's
    test_write_program_recon_handles_repo_asset_id_with_slashes: check the recorded
    path's filename, and that the actual file exists on disk at that name."""
    import json
    import recon_program as rp
    from recon.deps import Closure, Dep
    from recon.clone import CloneResult
    from recon.recon_item import _safe_asset_filename

    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(cloned=True, clone_path=str(dest), commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "infer_ecosystem", lambda src: "npm")
    monkeypatch.setattr(rp.deps, "infer_package_name", lambda src, eco: "minimatch")
    monkeypatch.setattr(rp.deps, "resolve_closure",
                        lambda src, eco: Closure(deps=[Dep("brace-expansion", "1.1.11", eco)],
                                                 lockfile="package-lock.json", total_before_cap=1))
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("ghsa-isaacs-minimatch",
                    {"asset_type": "repo", "identifier": "github.com/isaacs/minimatch", "ecosystem": None})
    rp.run_recon(scopes, recon_root=tmp_path, ts="t")

    recon_json = json.loads((tmp_path / "ghsa-isaacs-minimatch" / "recon.json").read_text(encoding="utf-8"))
    recorded_path = recon_json[0]["transitive_closure"]["path"]
    # relabeled identifier is "minimatch" (a bare package name, no separators to flatten)
    expected_filename = _safe_asset_filename("minimatch") + ".closure.jsonl"
    assert recorded_path.endswith(expected_filename), recorded_path
    actual_file = tmp_path / "ghsa-isaacs-minimatch" / "dep-graph" / expected_filename
    assert actual_file.exists(), f"recon.json points at {recorded_path!r} but no such file was written"


def test_run_recon_flags_closure_identifier_collision(tmp_path, monkeypatch):
    """Two in-scope assets resolving to the same post-relabel identifier must not
    silently overwrite one closure with the other — first-wins: the first asset's
    closure is what actually gets persisted to disk under the shared identifier, so
    the SECOND (colliding) item is the one flagged and whose own transitive_closure
    path is nulled (it cannot claim a path that doesn't hold its data). (No current
    fetcher can trigger this — GHSA emits exactly one in_scope asset, huntr assets
    are already package-typed and never relabeled — but the guard is cheap and the
    failure mode is silent data loss if it ever does occur.)"""
    import json
    import recon_program as rp
    from recon.deps import Closure, Dep
    from recon.clone import CloneResult

    monkeypatch.setattr(rp.clone, "clone_repo",
                        lambda repo, dest, **kw: CloneResult(
                            cloned=True, clone_path=str(dest / repo.rsplit("/", 1)[-1]), commit_sha="sha1"))
    monkeypatch.setattr(rp.deps, "infer_ecosystem", lambda src: "npm")
    monkeypatch.setattr(rp.deps, "infer_package_name", lambda src, eco: "same-name")

    def _resolve_closure(src, eco):
        # Distinguish the two assets' closures by their distinct clone paths ("one" vs
        # "two") so the test can prove which asset's real dependency data landed on disk.
        if str(src).endswith("one"):
            return Closure(deps=[Dep("dep-a", "1.0.0", eco)], lockfile="package-lock.json",
                           total_before_cap=1)
        return Closure(deps=[Dep("dep-b", "2.0.0", eco), Dep("dep-c", "3.0.0", eco)],
                       lockfile="package-lock.json", total_before_cap=2)

    monkeypatch.setattr(rp.deps, "resolve_closure", _resolve_closure)
    monkeypatch.setattr(rp.advisories, "correlate", lambda deps, disc, **kw: ([], []))

    scopes = _scope("ghsa-collision", [
        {"asset_type": "repo", "identifier": "github.com/a/one", "ecosystem": None},
        {"asset_type": "repo", "identifier": "github.com/b/two", "ecosystem": None},
    ])
    items = rp.run_recon(scopes, recon_root=tmp_path, ts="t")

    assert len(items) == 2
    assert any(f.startswith("closure_identifier_collision:") for f in items[1]["flags"])
    # The losing (second) item's own recorded path must be nulled — it never held its
    # own data, and pointing at the shared path would misattribute the first item's deps.
    assert items[1]["transitive_closure"]["path"] is None
    # The winning (first) item's path must point at a real file containing ITS deps.
    winning_path = items[0]["transitive_closure"]["path"]
    assert winning_path is not None
    from recon.recon_item import _safe_asset_filename
    closure_file = tmp_path / "ghsa-collision" / "dep-graph" / (_safe_asset_filename("same-name") + ".closure.jsonl")
    assert winning_path.endswith(closure_file.name)
    lines = [json.loads(l) for l in closure_file.read_text(encoding="utf-8").splitlines()]
    names = {d["name"] for d in lines}
    assert names == {"dep-a"}  # asset "one"'s real closure, not asset "two"'s
