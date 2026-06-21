"""fetch_program.py — dispatch to a venue fetcher, validate, and write scope.

Usage:
    python sec-research/scripts/fetch_program.py --venue huntr --identifier acme-org/acme-pkg
    python sec-research/scripts/fetch_program.py --venue ghsa  --identifier acme-org/acme-repo
    python sec-research/scripts/fetch_program.py --venue ibb-h1 --identifier django
    python sec-research/scripts/fetch_program.py --venue huntr --identifier acme-org/acme-pkg --force

On success:  writes programs/<slug>/scope.yaml (and the disclosed/ subdir), exits 0.
On draft:    writes programs/<slug>/scope.draft.yaml, prints warnings to stderr, exits 1.
On invalid:  writes programs/<slug>/scope.draft.yaml, prints schema errors to stderr, exits 1.
On failure:  writes NOTHING, prints error to stderr, exits 1.

This is the ONLY filesystem writer for fetched scopes.  scope.yaml is never
written unless the fetch succeeded (ok=True) AND validate_program passes AND
the result is not flagged as a draft.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Bootstrap: add hooks/ (lib/*) and scripts/ (fetchers/*) to sys.path so imports
# work identically whether this is invoked directly or imported in tests.
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SEC_RESEARCH = _SCRIPTS_DIR.parent
_HOOKS_DIR = _SEC_RESEARCH / "hooks"
for _p in (_HOOKS_DIR, _SCRIPTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from lib.policy import ScopeViolation  # noqa: E402
from lib.schema_validate import validate_program  # noqa: E402
from lib.scope_io import write_draft, write_scope  # noqa: E402
from fetchers import ghsa, huntr, ibb  # noqa: E402

# Venue-string → fetcher callable map.  Tests may patch this dict.
FETCHERS: dict[str, object] = {
    "huntr": huntr.fetch,
    "ghsa": ghsa.fetch,
    "ibb-h1": ibb.fetch,
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch a program scope from a venue API and write programs/<slug>/scope.yaml."
    )
    p.add_argument(
        "--venue",
        required=True,
        choices=sorted(FETCHERS),
        help="Venue to fetch from (huntr / ghsa / ibb-h1).",
    )
    p.add_argument(
        "--identifier",
        required=True,
        help="Venue-specific program identifier (e.g. 'acme-org/acme-pkg' for huntr).",
    )
    p.add_argument(
        "--from-fixture",
        default=None,
        help=(
            "Path to a canned fixture file; skips the live network call.  "
            "Passed as from_fixture to the fetcher.  For testing only."
        ),
    )
    p.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite an existing scope.yaml (default: refuse and exit 1).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0 = success, 1 = any error)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    venue = args.venue
    identifier = args.identifier
    fixture = Path(args.from_fixture) if args.from_fixture else None

    # Resolve fetcher callable
    fetch_fn = FETCHERS.get(venue)
    if fetch_fn is None:
        # Shouldn't happen because argparse enforces choices, but guard anyway.
        print(f"ERROR: unknown venue {venue!r}", file=sys.stderr)
        return 1

    # Dispatch to the venue fetcher.  ScopeViolation propagates here (no partial
    # write has happened) and is caught below.
    try:
        res = fetch_fn(identifier, from_fixture=fixture)
    except ScopeViolation as exc:
        print(f"ERROR: scope policy blocked the fetch — {exc}", file=sys.stderr)
        return 1

    # Fetch failure (e.g. bad identifier, parse error, HTTP error) — write nothing.
    if not res.ok:
        for w in res.warnings:
            print(f"ERROR: {w}", file=sys.stderr)
        if not res.warnings:
            print(f"ERROR: fetch failed for {venue} / {identifier}", file=sys.stderr)
        return 1

    # Draft result — validate for informational purposes, then write to draft.
    if res.draft:
        for w in res.warnings:
            print(f"WARNING: {w}", file=sys.stderr)
        ok, errors = validate_program(res.data)
        if not ok:
            print("WARNING: draft data also failed schema validation:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
        draft_path = write_draft(res.slug, res.data)
        print(f"Draft written (manual completion required): {draft_path}", file=sys.stderr)
        return 1

    # Non-draft success: validate before writing anything.
    ok, errors = validate_program(res.data)
    if not ok:
        print("ERROR: fetched scope failed schema validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        draft_path = write_draft(res.slug, res.data)
        print(f"Draft written for manual inspection: {draft_path}", file=sys.stderr)
        return 1

    # Write the live scope.yaml — raises FileExistsError without --force.
    try:
        scope_path = write_scope(res.slug, res.data, force=args.force)
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Re-run with --force to overwrite.", file=sys.stderr)
        return 1

    # Success output.
    if res.warnings:
        for w in res.warnings:
            print(f"WARNING: {w}", file=sys.stderr)
    print(f"Program fetched: {res.slug}")
    print(f"  Venue: {res.data['venue']}")
    print(f"  In-scope: {len(res.data.get('in_scope', []))} entries")
    print(f"  Out-of-scope: {len(res.data.get('out_of_scope', []))} entries")
    print(f"  Saved to: {scope_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
