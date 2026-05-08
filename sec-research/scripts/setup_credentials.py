"""setup_credentials.py — interactive keyring setup for venue API credentials.

Stage 1 doesn't NEED any populated credentials (ghsa uses gh CLI auth). This script
exists so the substrate is testable and so Stages 2/7 can populate venue creds easily.

Usage:
    python sec-research/scripts/setup_credentials.py <venue>
    python sec-research/scripts/setup_credentials.py --list
    python sec-research/scripts/setup_credentials.py --delete <venue>

Where <venue> is one of: huntr, h1, ibb-h1, bugcrowd, intigriti, github-pat (for direct API).
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from lib import credentials  # noqa: E402


VENUE_DEFINITIONS = {
    "huntr": {
        "service": "huntr-api",
        "credential_help": "huntr.com API token from https://huntr.com/settings/api",
    },
    "h1": {
        "service": "hackerone-api",
        "credential_help": "HackerOne API token from https://hackerone.com/users/api_tokens",
    },
    "ibb-h1": {
        "service": "hackerone-api",
        "credential_help": "Same as h1 — HackerOne IBB uses the same auth",
    },
    "bugcrowd": {
        "service": "bugcrowd-api",
        "credential_help": "Bugcrowd API token from researcher dashboard",
    },
    "intigriti": {
        "service": "intigriti-api",
        "credential_help": "Intigriti API token from researcher settings",
    },
    "github-pat": {
        "service": "github-pat",
        "credential_help": "GitHub fine-grained PAT (only needed for direct API; gh CLI handles ghsa flow)",
    },
}


def main() -> int:
    p = argparse.ArgumentParser(description="Interactive keyring credential setup.")
    p.add_argument("venue", nargs="?", help="Venue identifier (huntr, h1, ...)")
    p.add_argument("--list", action="store_true", help="List defined venues")
    p.add_argument("--delete", help="Delete a stored credential by venue name")
    p.add_argument("--username", help="Username for the credential (defaults to interactive prompt)")
    args = p.parse_args()

    if args.list:
        print("Defined venues:")
        for venue, info in VENUE_DEFINITIONS.items():
            print(f"  {venue:15s} service={info['service']!r}")
            print(f"  {'':15s} → {info['credential_help']}")
        return 0

    if args.delete:
        if args.delete not in VENUE_DEFINITIONS:
            print(f"ERROR: unknown venue: {args.delete}", file=sys.stderr)
            return 1
        info = VENUE_DEFINITIONS[args.delete]
        username = args.username or input(f"Username for {args.delete}: ").strip()
        if not username:
            print("ERROR: username required", file=sys.stderr)
            return 1
        credentials.delete_credential(info["service"], username)
        print(f"Deleted credential for {info['service']}/{username}")
        return 0

    if not args.venue:
        print("ERROR: venue argument required (or use --list)", file=sys.stderr)
        return 1
    if args.venue not in VENUE_DEFINITIONS:
        print(f"ERROR: unknown venue: {args.venue}", file=sys.stderr)
        print(f"Known venues: {', '.join(VENUE_DEFINITIONS.keys())}", file=sys.stderr)
        return 1

    info = VENUE_DEFINITIONS[args.venue]
    print(f"Setting up credential for {args.venue} ({info['service']})")
    print(f"  → {info['credential_help']}")

    username = args.username or input("Username for this credential: ").strip()
    if not username:
        print("ERROR: username required", file=sys.stderr)
        return 1

    secret = getpass.getpass(f"Paste credential for {info['service']}/{username} (input hidden): ")
    if not secret:
        print("ERROR: empty credential; aborting", file=sys.stderr)
        return 1

    try:
        credentials.set_credential(info["service"], username, secret)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Stored. Reference in scope.yaml:")
    print(f"  submission:")
    print(f"    auth_ref:")
    print(f"      service: {info['service']}")
    print(f"      username: {username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
