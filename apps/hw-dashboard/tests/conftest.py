"""Shared pytest fixtures for hw-dashboard.

`tmp_data` redirects every writable data path onto tmp_path so no test touches
the real data tree. SCHEMA_DIR is left pointing at the real schemas (they are the
contract under test, not fixtures).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """Point all writable data dirs at an isolated tmp tree and create them."""
    from collector import paths

    data = tmp_path / "data"
    mapping = {
        "DATA_DIR": data,
        "COMPONENTS_DIR": data / "components",
        "SKUS_DIR": data / "skus",
        "SEED_DIR": data / "seed",
        "SERIES_DIR": data / "series",
        "ANALYTICS_DIR": data / "analytics",
        "INTAKE_DIR": data / "intake",
        "MACHINE_PROFILE": data / "machine_profile.json",
        "RECOMMENDATION": data / "recommendation.json",
        "ANALYTICS_INDEX": data / "analytics" / "index.json",
        "RUN_LOG": data / "collector-runs.jsonl",
    }
    for name, value in mapping.items():
        monkeypatch.setattr(paths, name, value)
    for d in (
        mapping["COMPONENTS_DIR"],
        mapping["SKUS_DIR"],
        mapping["SEED_DIR"],
        mapping["SERIES_DIR"],
        mapping["ANALYTICS_DIR"],
        mapping["INTAKE_DIR"],
    ):
        d.mkdir(parents=True, exist_ok=True)
    return data
