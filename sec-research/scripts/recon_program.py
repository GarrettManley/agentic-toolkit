"""recon_program.py — Stage 3 Recon Module orchestrator.

Usage:
    python scripts/recon_program.py --slug <slug>
    python scripts/recon_program.py --all
    # tests drive run_recon() directly with monkeypatched units.

For each in-scope package/repo asset of each (selected) loaded scope, assemble a
recon item and write artifacts to runtime/recon/<slug>/. Egress is gated inside
the recon units (RECON_INFRA_HOSTS via policy.check_http). ScopeViolation
propagates to exit 1."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOKS_DIR = SCRIPTS_DIR.parent / "hooks"
for _p in (str(SCRIPTS_DIR), str(HOOKS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lib.policy import ScopeViolation                       # noqa: E402
from lib.scope_match import load_all_scopes                 # noqa: E402
from lib.paths import WORKSPACE_ROOT                        # noqa: E402
from recon import advisories, clone, deps, metadata         # noqa: E402
from recon.recon_item import build_recon_item, write_program_recon  # noqa: E402

_RECON_ASSET_TYPES = {"package", "repo"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recon_one_asset(slug, asset, disclosed_dir, source_root, ts):
    """Returns (item, closure) or raises ScopeViolation. Other errors → recon_error flag."""
    extra_flags: list[str] = []
    md = clone_res = None
    closure = deps.Closure(no_lockfile=True)
    resolved_asset = asset
    repo_id = None
    resolved_version = None
    try:
        eco = asset.get("ecosystem")
        eco_declared = bool(eco)
        if asset["asset_type"] == "package" and eco:
            md = metadata.fetch_metadata(asset["identifier"], eco)
        repo_id = md.repo_url if md else (asset["identifier"] if asset["asset_type"] == "repo" else None)
        if repo_id:
            clone_res = clone.clone_repo(repo_id, source_root)
            if clone_res.cloned and clone_res.clone_path:
                clone_path = Path(clone_res.clone_path)
                # repo assets may carry no ecosystem (e.g. GHSA) — infer from the clone.
                eco = eco or deps.infer_ecosystem(clone_path)
                if eco:
                    closure = deps.resolve_closure(clone_path, eco)
                    if asset["asset_type"] == "repo" and not eco_declared:
                        pkg_name = deps.infer_package_name(clone_path, eco)
                        if pkg_name:
                            resolved_asset = {"asset_type": "package", "identifier": pkg_name,
                                              "ecosystem": eco}
                            extra_flags.append("package_identity_inferred_from_repo")
                            resolved_version = deps.infer_package_version(clone_path, eco)
                            if not resolved_version:
                                extra_flags.append("package_version_unresolved")
                        else:
                            extra_flags.append("package_name_unresolved")
        advs, adv_errors = advisories.correlate(closure.deps, disclosed_dir)
        extra_flags += [f"advisory_source_error:{e.split(':')[0]}" for e in adv_errors]
    except ScopeViolation:
        raise
    except Exception as e:  # per-asset isolation — one bad asset doesn't sink the run
        extra_flags.append(f"recon_error:{type(e).__name__}")
        advs = []
    item = build_recon_item(slug, resolved_asset, md, closure, clone_res, advs, extra_flags,
                            ts=ts, repo_identifier=repo_id, resolved_version=resolved_version)
    return item, closure


def run_recon(scopes: dict, *, recon_root: Path | None = None, ts: str | None = None) -> list[dict]:
    recon_root = recon_root or (WORKSPACE_ROOT / "runtime" / "recon")
    ts = ts or _utc_now_iso()
    all_items: list[dict] = []
    for slug, scope in scopes.items():
        disclosed_dir = WORKSPACE_ROOT / "programs" / slug / "disclosed"
        source_root = recon_root / slug / "source"
        items, closures = [], {}
        for asset in scope.get("in_scope", []):
            if asset.get("asset_type") not in _RECON_ASSET_TYPES:
                continue
            item, closure = _recon_one_asset(slug, asset, disclosed_dir, source_root, ts)
            item_id = item["asset"]["identifier"]
            if item_id in closures:
                item["flags"].append(f"closure_identifier_collision:{item_id}")
            items.append(item)
            closures[item_id] = closure
        if items:
            write_program_recon(slug, items, closures, recon_root)
        all_items.extend(items)
    return all_items


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 3 recon over loaded program scopes.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--slug", help="Run recon for a single loaded program slug")
    g.add_argument("--all", action="store_true", help="Run recon for every loaded scope")
    args = p.parse_args(argv)

    scopes = load_all_scopes()
    if args.slug:
        scopes = {args.slug: scopes[args.slug]} if args.slug in scopes else {}
        if not scopes:
            print(f"ERROR: no loaded scope for slug {args.slug!r}", file=sys.stderr)
            return 1
    try:
        items = run_recon(scopes)
    except ScopeViolation as e:
        print(f"ERROR (PT-1): {e}", file=sys.stderr)
        return 1
    print(f"Recon complete: {len(items)} asset(s) across {len(scopes)} program(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
