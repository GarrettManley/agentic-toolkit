"""sign_override.py — interactive issuance of HMAC-signed override tokens.

Usage:
    python sec-research/scripts/sign_override.py --rule PT-1 --target registry.npmjs.org \
        --reason "querying public registry for package metadata"
    [--max-uses 1] [--ttl-hours 4] [--trace-id FIND-...] [--test-mode-confirm]

The --test-mode-confirm flag is for tests only; it skips the interactive confirmation.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib.paths import OVERRIDES_SIGNED_DIR  # noqa: E402
from lib.sign_verify import sign_token, canonical_json  # noqa: E402
from lib import ledger  # noqa: E402

ALLOWED_RULES = {
    "PT-1", "PT-3", "PT-4", "PT-5",
    "PoT-2", "PoT-3",
    "S-1", "S-2",
    "UPS-2",
    "G-1", "G-4",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _next_token_id() -> str:
    today = _utc_now().strftime("%Y-%m-%d")
    counter = 1
    if OVERRIDES_SIGNED_DIR.exists():
        for p in OVERRIDES_SIGNED_DIR.glob(f"ovr-{today}-*.json"):
            m = re.search(r"ovr-\d{4}-\d{2}-\d{2}-(\d{3})", p.name)
            if m:
                n = int(m.group(1))
                if n >= counter:
                    counter = n + 1
    return f"ovr-{today}-{counter:03d}"


def main() -> int:
    p = argparse.ArgumentParser(description="Sign an override token (interactive).")
    p.add_argument("--rule", required=True, choices=sorted(ALLOWED_RULES),
                   help="Rule ID to override (PT-2/PT-6/G-2 are NOT in this list — they have no override path)")
    p.add_argument("--target", required=True, help="Specific target this override applies to")
    p.add_argument("--reason", required=True, help="Human-readable explanation (≥20 chars)")
    p.add_argument("--max-uses", type=int, default=1, help="Number of uses (1-5; default 1)")
    p.add_argument("--ttl-hours", type=float, default=4.0, help="TTL in hours (max 24; default 4)")
    p.add_argument("--trace-id", help="Optional finding trace_id this scoped to")
    p.add_argument("--created-by", default=None, help="Identity (default: $USER or $USERNAME)")
    p.add_argument("--test-mode-confirm", action="store_true", help="Skip interactive confirmation (TESTS ONLY)")
    args = p.parse_args()

    if len(args.reason) < 20:
        print(f"ERROR: reason must be ≥20 chars (got {len(args.reason)})", file=sys.stderr)
        return 1
    if args.max_uses < 1 or args.max_uses > 5:
        print(f"ERROR: max_uses must be 1-5 (got {args.max_uses})", file=sys.stderr)
        return 1
    if args.ttl_hours < 0 or args.ttl_hours > 24:
        print(f"ERROR: ttl-hours must be 0-24 (got {args.ttl_hours})", file=sys.stderr)
        return 1

    import os
    created_by = args.created_by or os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"

    now = _utc_now()
    expires_at = now + timedelta(hours=args.ttl_hours)
    token_id = _next_token_id()

    payload = {
        "token_id": token_id,
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_by": created_by,
        "rule_id": args.rule,
        "scope": {
            "target": args.target,
            "reason": args.reason,
        },
        "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_uses": args.max_uses,
    }
    if args.trace_id:
        payload["scope"]["trace_id"] = args.trace_id

    # Display + confirm
    print("\n" + "=" * 70)
    print("  OVERRIDE TOKEN ISSUANCE — Confirm to sign")
    print("=" * 70)
    print(f"  Token ID    : {token_id}")
    print(f"  Rule        : {args.rule}")
    print(f"  Target      : {args.target}")
    print(f"  Reason      : {args.reason}")
    print(f"  Created by  : {created_by}")
    print(f"  Expires at  : {payload['expires_at']}")
    print(f"  Max uses    : {args.max_uses}")
    if args.trace_id:
        print(f"  Trace ID    : {args.trace_id}")
    print("=" * 70)

    if args.test_mode_confirm:
        confirmed = True
    else:
        try:
            answer = input(f"\nType the rule ID ({args.rule}) to confirm: ").strip()
        except EOFError:
            print("ERROR: no input received; aborting", file=sys.stderr)
            return 1
        confirmed = answer == args.rule

    if not confirmed:
        print("Aborted (input didn't match rule ID).")
        return 1

    # Sign + write
    try:
        signature = sign_token(payload)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload["signature"] = signature
    OVERRIDES_SIGNED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OVERRIDES_SIGNED_DIR / f"{token_id}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Ledger
    ledger.append_event(
        "override-issued",
        override_token_id=token_id,
        rule_id=args.rule,
        trace_id=args.trace_id,
        actor=created_by,
        notes=f"target={args.target}; reason={args.reason}",
    )

    print(f"\nToken signed and written to: {out_path}")
    print(f"Use within {args.max_uses} time(s) before {payload['expires_at']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
