"""investigate.py — on-demand deep-dive entry point (Stage 1 SKELETON).

Same pipeline as nightly.py but bounded to a single program / asset and interactive.

Usage:
    python scripts/investigate.py <program-slug> [--asset <identifier>]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib.paths import PROGRAMS_DIR  # noqa: E402
from lib.scope_match import load_all_scopes  # noqa: E402

# Reuse stages from nightly.py
import nightly  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="On-demand investigation deep-dive (Stage 1 skeleton).")
    p.add_argument("program_slug")
    p.add_argument("--asset", help="Specific in-scope asset to focus on")
    args = p.parse_args()

    scopes = load_all_scopes()
    if args.program_slug not in scopes:
        print(f"ERROR: program {args.program_slug!r} not loaded.", file=sys.stderr)
        print(f"Available: {', '.join(scopes.keys()) or '<none>'}", file=sys.stderr)
        print(f"Load via: python scripts/load_program.py --from-file <path>", file=sys.stderr)
        return 1

    target_scope = {args.program_slug: scopes[args.program_slug]}
    print(f"Investigating: {args.program_slug}")
    if args.asset:
        print(f"  Bounded to asset: {args.asset}")

    print("\n=== Stage 1 SKELETON pipeline ===")
    print("(Stages 3-5 are stubs; this proves the framework + hooks + ledger work end-to-end)\n")

    refresh_log = nightly.stage_refresh_scopes(target_scope)
    for line in refresh_log:
        print(f"  scope: {line}")

    recon = nightly.stage_recon(target_scope)
    print(f"  recon: {len(recon)} items (Stage 3 stub)")

    hypotheses = nightly.stage_hypothesize(target_scope, recon)
    print(f"  hypotheses: {len(hypotheses)} (Stage 4 stub)")

    verified = nightly.stage_verify(hypotheses)
    print(f"  verified: {sum(1 for v in verified if v.get('verified'))} (Stage 4 stub)")

    drafts = nightly.stage_draft_findings(verified)
    print(f"  drafts: {len(drafts)} (Stage 6 stub)")

    briefing = nightly.stage_briefing(target_scope, recon, hypotheses, verified, drafts)
    print(f"\nBriefing: {briefing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
