"""Assemble, validate, and persist per-asset recon items (the Stage 4 contract).

build_recon_item derives flags from the closure (no_lockfile / closure_truncated)
and clone (clone_skipped:*) plus any extra_flags (e.g. advisory_source_error:*).
write_program_recon persists recon.json + per-asset closure jsonl under
runtime/recon/<slug>/."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "recon_item.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _safe_asset_filename(asset_id: str) -> str:
    """Flatten an asset identifier into a single filesystem-safe filename stem.

    Repo/ecosystem asset ids contain path separators (e.g. a GHSA repo asset is
    ``github.com/isaacs/minimatch``); embedding them raw produced unintended nested
    directories that were never created. Flatten ``/``, ``\\`` and ``:`` so the closure
    jsonl is always a single file under dep-graph/."""
    return asset_id.replace("\\", "/").replace("/", "__").replace(":", "_")


def _closure_path(slug: str, asset_id: str) -> str:
    return f"runtime/recon/{slug}/dep-graph/{_safe_asset_filename(asset_id)}.closure.jsonl"


def build_recon_item(slug, asset, metadata, closure, clone_result, advisories,
                     extra_flags, *, ts, repo_identifier=None):
    flags = list(extra_flags)
    if closure.no_lockfile:
        flags.append("no_lockfile")
    if closure.truncated:
        flags.append("closure_truncated")
    repo = None
    if clone_result is not None:
        if not clone_result.cloned and clone_result.skipped_reason:
            flags.append(f"clone_skipped:{clone_result.skipped_reason}")
        repo = {
            "identifier": (repo_identifier if repo_identifier is not None
                          else (metadata.repo_url if metadata else None)),
            "clone_path": clone_result.clone_path,
            "commit_sha": clone_result.commit_sha,
            "cloned": clone_result.cloned,
        }
    return {
        "slug": slug,
        "asset": {"asset_type": asset["asset_type"], "identifier": asset["identifier"],
                  "ecosystem": asset.get("ecosystem")},
        "resolved_version": (metadata.latest if metadata else None),
        "repo": repo,
        "direct_deps": [asdict(d) for d in closure.direct],
        "transitive_closure": {
            "count": len(closure.deps),
            "truncated": closure.truncated,
            "path": _closure_path(slug, asset["identifier"]) if closure.deps else None,
        },
        "known_advisories": [asdict(a) for a in advisories],
        "flags": flags,
        "recon_ts": ts,
    }


def validate_recon_item(item: dict) -> tuple[bool, list[str]]:
    validator = jsonschema.Draft202012Validator(_SCHEMA)
    errors = [e.message for e in validator.iter_errors(item)]
    return (not errors), errors


def write_program_recon(slug, items, closures, recon_root: Path) -> Path:
    prog_dir = recon_root / slug
    (prog_dir / "dep-graph").mkdir(parents=True, exist_ok=True)
    for asset_id, closure in closures.items():
        if not closure.deps:
            continue
        lines = "\n".join(json.dumps(asdict(d)) for d in closure.deps)
        (prog_dir / "dep-graph" / f"{_safe_asset_filename(asset_id)}.closure.jsonl").write_text(
            lines + "\n", encoding="utf-8")
    recon_json = prog_dir / "recon.json"
    recon_json.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return recon_json
