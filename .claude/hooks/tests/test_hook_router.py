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


import pytest


@pytest.mark.parametrize("matcher,tool,expected", [
    (None, "Edit", True),
    ("", "Edit", True),
    ("*", "Edit", True),
    (".*", "Bash", True),
    ("Edit|Write", "Edit", True),
    ("Edit|Write", "Bash", False),
    ("Bash", "Bash", True),
    ("^WebFetch$", "WebFetch", True),
    ("[unclosed", "Edit", False),  # malformed regex -> no match, no crash
])
def test_matcher_matches(matcher, tool, expected):
    import hook_router_lib as lib
    assert lib.matcher_matches(matcher, tool) is expected


def test_resolve_command_substitutes_project_dir(tmp_path):
    import hook_router_lib as lib
    child = tmp_path / "sec-research"
    argv = lib.resolve_command("python ${CLAUDE_PROJECT_DIR}/hooks/pretooluse.py", child)
    assert argv == ["python", f"{child.as_posix()}/hooks/pretooluse.py"]


import sys
from pathlib import Path

STUBS = Path(__file__).resolve().parent / "stubs"


def test_run_child_replays_stdin_and_sets_env(tmp_path):
    import hook_router_lib as lib
    child = tmp_path / "proj"; child.mkdir()
    argv = [sys.executable, str(STUBS / "echo_hook.py")]
    rc, out, err = lib.run_child_hook(argv, child, b'{"hook_event_name":"PreToolUse"}', 15)
    assert rc == 0
    assert "echo:len=32" in out                      # exact bytes were replayed to stdin
    assert f"cpd={child}" in out                      # CLAUDE_PROJECT_DIR was set to child


def test_run_child_block(tmp_path):
    import hook_router_lib as lib
    child = tmp_path / "proj"; child.mkdir()
    rc, out, err = lib.run_child_hook([sys.executable, str(STUBS / "block_hook.py")], child, b"{}", 15)
    assert rc == 2
    assert "stub block" in err


def test_run_child_spawn_failure_is_fail_open(tmp_path):
    import hook_router_lib as lib
    child = tmp_path / "proj"; child.mkdir()
    rc, out, err = lib.run_child_hook(["definitely-not-a-real-binary-xyz"], child, b"{}", 15)
    assert rc == 0                                    # fail-open on spawn failure
    assert err                                        # but diagnostic surfaced


# ---------------------------------------------------------------------------
# Task 3: aggregate + route_event
# ---------------------------------------------------------------------------

def test_aggregate_block_wins():
    import hook_router_lib as lib
    rc, out, err = lib.aggregate("PreToolUse", [(0, "a", ""), (2, "", "blocked!"), (0, "b", "")])
    assert rc == 2 and err == "blocked!" and out == ""


def test_aggregate_concats_when_no_block():
    import hook_router_lib as lib
    rc, out, err = lib.aggregate("UserPromptSubmit", [(0, "ctx1", ""), (0, "ctx2", "warn")])
    assert rc == 0 and out == "ctx1ctx2" and "warn" in err


def test_route_event_blocks_on_child_exit2(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    cmd = f"{Path(sys.executable).as_posix()} {(STUBS / 'block_hook.py').as_posix()}"
    mk("sec-research", {"PreToolUse": [{"matcher": ".*", "hooks": [{"command": cmd}]}]})
    event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"}).encode()
    rc, out, err = lib.route_event(event, root, lib.load_config(root / "x.json"))
    assert rc == 2 and "stub block" in err


def test_route_event_passes_when_matcher_excludes(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    cmd = f"{Path(sys.executable).as_posix()} {(STUBS / 'block_hook.py').as_posix()}"
    mk("sec-research", {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": cmd}]}]})
    event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"}).encode()
    rc, out, err = lib.route_event(event, root, lib.load_config(root / "x.json"))
    assert rc == 0  # blocker's matcher (Bash) didn't match tool_name Edit -> never invoked


def test_route_event_userpromptsubmit_concats_stdout(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    cmd = f"{Path(sys.executable).as_posix()} {(STUBS / 'echo_hook.py').as_posix()}"
    mk("a", {"UserPromptSubmit": [{"hooks": [{"command": cmd}]}]})
    mk("b", {"UserPromptSubmit": [{"hooks": [{"command": cmd}]}]})
    event = json.dumps({"hook_event_name": "UserPromptSubmit"}).encode()
    rc, out, err = lib.route_event(event, root, lib.load_config(root / "x.json"))
    assert rc == 0 and out.count("echo:") == 2


def test_route_event_unparseable_is_fail_open(fake_root):
    import hook_router_lib as lib
    root, _ = fake_root
    rc, out, err = lib.route_event(b"not json", root, lib.load_config(root / "x.json"))
    assert rc == 0 and out == "" and err == ""
