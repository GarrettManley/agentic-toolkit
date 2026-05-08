"""load_program.py — ingest a program scope (validate + write to programs/<slug>/scope.yaml).

Stage 1: this is a manual ingest tool. Stage 2 will provide automated venue-API fetchers.

Usage:
    # From a YAML file:
    python sec-research/scripts/load_program.py --from-file path/to/scope.yaml

    # Generate a scaffold for manual editing:
    python sec-research/scripts/load_program.py --scaffold --venue ghsa --slug acme-org-acme-pkg
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib.paths import PROGRAMS_DIR  # noqa: E402
from lib.schema_validate import validate_program  # noqa: E402
from lib.scope_match import invalidate_scope_cache  # noqa: E402


SCAFFOLD_TEMPLATE = """\
program_slug: {slug}
venue: {venue}
loaded_at: {loaded_at}
loaded_from: <fill-in-the-source-URL>
display_name: <fill-in-display-name>

in_scope:
  - asset_type: package
    identifier: <pkg-name>
    ecosystem: <npm|pypi|cargo|...>
    tier: high
    max_payout_usd: 0
  - asset_type: repo
    identifier: github.com/<owner>/<repo>

out_of_scope: []

rules:
  ai_assistance_allowed: true
  ai_disclosure_required: true
  rate_limit_per_min: 60
  user_agent_required: "Garrett-Manley-SecResearch/1.0"
  no_dast_against_prod: true
  embargo_period_days: 90

submission:
  protocol: <huntr-api|ghsa-cli|manual-form|...>
  endpoint: <URL or mailto:>
  auth_ref:
    service: <keyring-service-name>
    username: <keyring-username>
"""


def main() -> int:
    p = argparse.ArgumentParser(description="Load (validate + write) a program scope.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-file", help="Load scope from a YAML file and write it to programs/<slug>/")
    g.add_argument("--scaffold", action="store_true", help="Write a template scope.yaml for manual editing")
    p.add_argument("--slug", help="Required with --scaffold or to override slug from --from-file")
    p.add_argument("--venue", help="Required with --scaffold")
    args = p.parse_args()

    if args.scaffold:
        if not args.slug or not args.venue:
            print("ERROR: --scaffold requires --slug and --venue", file=sys.stderr)
            return 1
        program_dir = PROGRAMS_DIR / args.slug
        if program_dir.exists() and (program_dir / "scope.yaml").exists():
            print(f"ERROR: {program_dir / 'scope.yaml'} already exists; refusing to overwrite", file=sys.stderr)
            return 1
        program_dir.mkdir(parents=True, exist_ok=True)
        (program_dir / "disclosed").mkdir(exist_ok=True)
        scope_path = program_dir / "scope.yaml"
        scope_path.write_text(
            SCAFFOLD_TEMPLATE.format(
                slug=args.slug,
                venue=args.venue,
                loaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            encoding="utf-8",
        )
        (program_dir / "notes.md").write_text(f"# Program notes: {args.slug}\n\n", encoding="utf-8")
        (program_dir / "targets.txt").write_text("", encoding="utf-8")
        print(f"Scaffold written to: {scope_path}")
        print("Edit the file and re-run: python sec-research/scripts/load_program.py --from-file " + str(scope_path))
        return 0

    # --from-file
    src = Path(args.from_file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 1
    try:
        import yaml
        with src.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except ImportError:
        print("ERROR: PyYAML not installed. Run: pip install pyyaml (or uv add pyyaml).", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: failed to parse YAML: {exc}", file=sys.stderr)
        return 1

    ok, errors = validate_program(data)
    if not ok:
        print("ERROR: scope failed schema validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    slug = args.slug or data["program_slug"]
    program_dir = PROGRAMS_DIR / slug
    program_dir.mkdir(parents=True, exist_ok=True)
    (program_dir / "disclosed").mkdir(exist_ok=True)
    scope_path = program_dir / "scope.yaml"

    with scope_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)

    invalidate_scope_cache()
    print(f"Program loaded: {slug}")
    print(f"  Venue: {data['venue']}")
    print(f"  In-scope: {len(data.get('in_scope', []))} entries")
    print(f"  Out-of-scope: {len(data.get('out_of_scope', []))} entries")
    print(f"  Saved to: {scope_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
