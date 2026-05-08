"""Common path constants for sec-research/."""
from __future__ import annotations

from pathlib import Path

# This file is at sec-research/hooks/lib/paths.py
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

# Workspace subdirs
DOCS_DIR = WORKSPACE_ROOT / "docs"
SCHEMA_DIR = WORKSPACE_ROOT / "schema"
HOOKS_DIR = WORKSPACE_ROOT / "hooks"
PROGRAMS_DIR = WORKSPACE_ROOT / "programs"
FINDINGS_DIR = WORKSPACE_ROOT / "findings"
PLAYBOOKS_DIR = WORKSPACE_ROOT / "playbooks"
SUBMISSIONS_DIR = WORKSPACE_ROOT / "submissions"
SUBMISSIONS_TOKENS_DIR = SUBMISSIONS_DIR / "tokens"
LEDGER_PATH = SUBMISSIONS_DIR / "ledger.jsonl"
OVERRIDES_DIR = WORKSPACE_ROOT / "overrides"
OVERRIDES_PENDING_DIR = OVERRIDES_DIR / "pending"
OVERRIDES_SIGNED_DIR = OVERRIDES_DIR / "signed"
OVERRIDES_USED_DIR = OVERRIDES_DIR / "used"
RUNTIME_DIR = WORKSPACE_ROOT / "runtime"
RUNTIME_SANDBOX_DIR = RUNTIME_DIR / "sandbox"
RUNTIME_RECON_DIR = RUNTIME_DIR / "recon"
RUNTIME_BRIEFINGS_DIR = RUNTIME_DIR / "briefings"
RUNTIME_SESSIONS_DIR = RUNTIME_DIR / "sessions"
RUNTIME_FEEDBACK_QUEUE = RUNTIME_DIR / "feedback-queue.jsonl"
RUNTIME_SCHEDULED_RUNS = RUNTIME_DIR / "scheduled-runs.jsonl"
RUNTIME_CACHE_DIR = RUNTIME_DIR / "cache"
RUNTIME_CACHE_NVD_DIR = RUNTIME_CACHE_DIR / "nvd"
RUNTIME_CACHE_REGISTRY_DIR = RUNTIME_CACHE_DIR / "registry"
RUNTIME_CACHE_GIT_DIR = RUNTIME_CACHE_DIR / "git"
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"

# External (outside repo)
HOME = Path.home()
OVERRIDE_KEY_PATH = HOME / ".claude" / "sec-research-override-key"
