"""
init_workspace.py — Idempotent verifier and bootstrapper for sec-research/.

Run with no args to verify (and create-if-missing) the full workspace structure.
Run with --verify to only check (no creates); exits non-zero on drift.
Run with --check-override-key to verify HMAC override key is present and well-formed.

Stage 1 ships this script as a structure-and-schema sanity check. Stages 2-7 may
extend it to verify additional fixtures.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent  # sec-research/
HOME = Path.home()
OVERRIDE_KEY_PATH = HOME / ".claude" / "sec-research-override-key"

EXPECTED_DIRS = [
    ".claude",
    "docs",
    "schema",
    "hooks",
    "hooks/lib",
    "programs",
    "findings",
    "playbooks",
    "playbooks/_meta",
    "submissions",
    "submissions/tokens",
    "overrides",
    "overrides/pending",
    "overrides/signed",
    "overrides/used",
    "runtime",
    "runtime/sandbox",
    "runtime/recon",
    "runtime/briefings",
    "runtime/sessions",
    "runtime/cache",
    "runtime/cache/nvd",
    "runtime/cache/registry",
    "runtime/cache/git",
    "scripts",
    "tests",
    "tests/hooks",
    "tests/schemas",
    "tests/e2e",
    "tests/fixtures",
    "tests/fixtures/huntr-test-program",
    "tests/fixtures/huntr-test-program/disclosed",
    "tests/fixtures/mock-venue",
]

EXPECTED_FILES = [
    "README.md",
    ".gitignore",
    ".hugoignore-marker",
    ".claude/settings.json",
    "docs/CHARTER.md",
    "docs/HOOK_CONTRACTS.md",
    "docs/SCOPE_SCHEMA.md",
    "docs/EVIDENCE_DISCIPLINE.md",
    "docs/SUBMISSION_GATE.md",
    "docs/PLAYBOOK_FORMAT.md",
    "docs/CREDENTIAL_HANDLING.md",
    "docs/INDEX.md",
    "schema/program.schema.json",
    "schema/finding.schema.json",
    "schema/evidence.schema.json",
    "schema/override.schema.json",
    "schema/submission.schema.json",
]


def ensure_dir(rel: str, create: bool) -> bool:
    p = WORKSPACE_ROOT / rel
    if p.exists():
        return True
    if create:
        p.mkdir(parents=True, exist_ok=True)
        return True
    return False


def check_file(rel: str) -> bool:
    return (WORKSPACE_ROOT / rel).is_file()


def validate_schema(rel: str) -> tuple[bool, str | None]:
    p = WORKSPACE_ROOT / rel
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Sanity check: schemas must declare $schema
        if "$schema" not in data:
            return False, f"missing $schema declaration"
        if not data["$schema"].startswith("https://json-schema.org/draft/"):
            return False, f"$schema not pointing at json-schema.org draft URL"
        # Try import jsonschema for full validation if available
        try:
            from jsonschema import Draft202012Validator
            Draft202012Validator.check_schema(data)
        except ImportError:
            # jsonschema not installed: do basic validation only
            if "type" not in data and "$ref" not in data and "$defs" not in data:
                return False, f"top-level lacks 'type', '$ref', or '$defs'"
        except Exception as exc:
            return False, f"invalid JSON Schema: {exc}"
        return True, None
    except Exception as exc:
        return False, f"failed to load: {exc}"


def validate_settings_json() -> tuple[bool, str | None]:
    p = WORKSPACE_ROOT / ".claude" / "settings.json"
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "hooks" not in data:
            return False, "missing 'hooks' key"
        for event in ("PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"):
            if event not in data["hooks"]:
                return False, f"missing hook event: {event}"
        return True, None
    except Exception as exc:
        return False, f"failed to load: {exc}"


def check_override_key() -> tuple[bool, str | None]:
    if not OVERRIDE_KEY_PATH.exists():
        return False, f"key file not found at {OVERRIDE_KEY_PATH} — generate via: python -c \"import secrets; print(secrets.token_hex(32))\" > {OVERRIDE_KEY_PATH}"
    content = OVERRIDE_KEY_PATH.read_text(encoding="utf-8").strip()
    if len(content) < 32:
        return False, f"key too short ({len(content)} chars); expected at least 32 hex chars"
    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize/verify sec-research workspace.")
    parser.add_argument("--verify", action="store_true", help="Verify only; do not create missing dirs")
    parser.add_argument("--check-override-key", action="store_true", help="Also check ~/.claude/sec-research-override-key")
    args = parser.parse_args()

    create = not args.verify
    issues: list[str] = []
    okays: list[str] = []

    print(f"sec-research/ at {WORKSPACE_ROOT}")
    print(f"Mode: {'VERIFY-ONLY' if args.verify else 'CREATE-IF-MISSING'}\n")

    # Directories
    print("== Directories ==")
    for d in EXPECTED_DIRS:
        ok = ensure_dir(d, create=create)
        if ok:
            okays.append(f"dir   {d}")
        else:
            issues.append(f"MISSING dir: {d}")

    # Files
    print("== Files ==")
    for f in EXPECTED_FILES:
        if check_file(f):
            okays.append(f"file  {f}")
        else:
            issues.append(f"MISSING file: {f}")

    # Schemas
    print("== Schema validation ==")
    for f in EXPECTED_FILES:
        if not f.startswith("schema/"):
            continue
        if not check_file(f):
            continue  # already reported as missing
        ok, err = validate_schema(f)
        if ok:
            okays.append(f"schema {f}")
        else:
            issues.append(f"INVALID schema {f}: {err}")

    # settings.json
    print("== Claude settings.json ==")
    if check_file(".claude/settings.json"):
        ok, err = validate_settings_json()
        if ok:
            okays.append("settings.json")
        else:
            issues.append(f"INVALID settings.json: {err}")

    # Override key (optional check)
    if args.check_override_key:
        print("== Override HMAC key ==")
        ok, err = check_override_key()
        if ok:
            okays.append(f"override-key {OVERRIDE_KEY_PATH}")
        else:
            issues.append(f"OVERRIDE KEY: {err}")

    # Report
    print(f"\n{len(okays)} OK / {len(issues)} issues")
    if issues:
        print("\nIssues:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("Workspace healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
