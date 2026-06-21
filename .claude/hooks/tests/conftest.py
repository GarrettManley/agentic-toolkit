import json
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent  # .claude/hooks/
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def _make_project(root: Path, name: str, event_hooks: dict):
    """Create <root>/<name>/.claude/settings.json with the given hooks block."""
    proj = root / name
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": event_hooks}), encoding="utf-8")
    return proj


@pytest.fixture
def fake_root(tmp_path):
    """A Workspace-like root. Returns (root, make_project) so tests build child projects."""
    return tmp_path, lambda name, event_hooks={}: _make_project(tmp_path, name, event_hooks)
