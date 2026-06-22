"""Path constants for the hw-dashboard backend. Rooted at apps/hw-dashboard/.

This file is at apps/hw-dashboard/collector/paths.py, so the app root is two
parents up. Tests monkeypatch these onto a tmp_path (see tests/conftest.py).
"""

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_DIR = APP_ROOT / "schema"
DATA_DIR = APP_ROOT / "data"

COMPONENTS_DIR = DATA_DIR / "components"
SKUS_DIR = DATA_DIR / "skus"
SEED_DIR = DATA_DIR / "seed"
SERIES_DIR = DATA_DIR / "series"
ANALYTICS_DIR = DATA_DIR / "analytics"
INTAKE_DIR = DATA_DIR / "intake"

MACHINE_PROFILE = DATA_DIR / "machine_profile.json"
RECOMMENDATION = DATA_DIR / "recommendation.json"
ANALYTICS_INDEX = ANALYTICS_DIR / "index.json"
RUN_LOG = DATA_DIR / "collector-runs.jsonl"


def series_path(sku_id: str) -> Path:
    return SERIES_DIR / f"{sku_id}.jsonl"


def seed_path(sku_id: str) -> Path:
    return SEED_DIR / f"{sku_id}.seed.jsonl"


def analytics_path(sku_id: str) -> Path:
    return ANALYTICS_DIR / f"{sku_id}.json"
