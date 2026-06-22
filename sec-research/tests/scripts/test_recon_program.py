from pathlib import Path


def _scope(slug, asset):
    return {slug: {"program_slug": slug, "venue": "huntr", "in_scope": [asset],
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
