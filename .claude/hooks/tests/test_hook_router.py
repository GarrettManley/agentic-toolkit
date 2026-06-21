import json


def test_discover_finds_child_with_settings(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    mk("sec-research", {"PreToolUse": [{"matcher": ".*", "hooks": [{"command": "python x.py"}]}]})
    projects = lib.discover_projects(root, lib.load_config(root / "nope.json"))
    names = [p.dir.name for p in projects]
    assert names == ["sec-research"]
    assert projects[0].settings["hooks"]["PreToolUse"][0]["matcher"] == ".*"


def test_discover_excludes_corporate_repos(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    mk("Duracell-Quantum", {"PreToolUse": [{"hooks": [{"command": "python evil.py"}]}]})
    mk("malachite", {"PreToolUse": [{"hooks": [{"command": "python evil.py"}]}]})
    mk("sec-research", {"PreToolUse": [{"hooks": [{"command": "python ok.py"}]}]})
    names = [p.dir.name for p in lib.discover_projects(root, lib.load_config(root / "nope.json"))]
    assert names == ["sec-research"]  # corporate dirs never federated


def test_discover_honors_user_ignore(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    mk("sec-research", {"PreToolUse": [{"hooks": [{"command": "python ok.py"}]}]})
    mk("scratch", {"PreToolUse": [{"hooks": [{"command": "python ok.py"}]}]})
    cfg = {"enabled": True, "ignore": ["scratch"], "timeout_seconds": 15}
    names = [p.dir.name for p in lib.discover_projects(root, cfg)]
    assert names == ["sec-research"]


def test_discover_skips_dirs_without_settings(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    (root / "plain-dir").mkdir()
    mk("sec-research", {"PreToolUse": [{"hooks": [{"command": "python ok.py"}]}]})
    names = [p.dir.name for p in lib.discover_projects(root, lib.load_config(root / "nope.json"))]
    assert names == ["sec-research"]


def test_load_config_defaults_when_missing(tmp_path):
    import hook_router_lib as lib
    cfg = lib.load_config(tmp_path / "absent.json")
    assert cfg == {"enabled": True, "ignore": [], "timeout_seconds": 15}
