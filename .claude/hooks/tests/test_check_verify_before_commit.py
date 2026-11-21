"""Tests for the Workspace commit gate, driven the way Claude Code drives it:
a JSON event on stdin, a JSON reply (or nothing) on stdout.

The rule under test: the gate may deny a commit, and may leave a note, but it
never answers "allow". An "allow" from a PreToolUse hook skips the user's
permission prompt for that command.

Levels: the first three cases are unit tests of the hook's public interface.
The cases that use `gate_root` are integration tests of one external point each
(git's staged-file list, or the verification scripts run through pwsh); they
cannot be pushed lower because the decision is made from those processes' output.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "check_verify_before_commit.py"
SCRIPTS = ("pre_commit_audit.ps1", "verify_workspace.ps1")


def _run(hook: Path, stdin: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "WORKSPACE_VERIFY_OVERRIDE"}
    return subprocess.run([sys.executable, str(hook)], input=stdin, capture_output=True,
                          text=True, env=env, timeout=60)


def _event(command: str) -> str:
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                       "tool_input": {"command": command}})


@pytest.fixture
def gate_root(tmp_path):
    """A stand-in Workspace root: a git repo holding a copy of the hook and both
    verification scripts. Returns (hook_path, stage, set_script_exit)."""
    root = tmp_path / "ws"
    (root / ".claude" / "hooks").mkdir(parents=True)
    (root / "_scripts").mkdir()
    hook = root / ".claude" / "hooks" / HOOK.name
    shutil.copy(HOOK, hook)
    for name in SCRIPTS:
        (root / "_scripts" / name).write_text("exit 0\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True,
                   stdin=subprocess.DEVNULL)

    def stage(rel: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "--", rel], check=True,
                       capture_output=True, stdin=subprocess.DEVNULL)

    def set_script_exit(name: str, code: int) -> None:
        (root / "_scripts" / name).write_text(f"Write-Output 'audit says no'\nexit {code}\n",
                                              encoding="utf-8")

    return hook, stage, set_script_exit


# --- commands the gate has no opinion on --------------------------------------

def test_a_command_that_is_not_a_commit_gets_no_reply():
    proc = _run(HOOK, _event("ls -la"))
    assert (proc.returncode, proc.stdout) == (0, "")


def test_unreadable_input_gets_no_reply():
    proc = _run(HOOK, "{not json")
    assert (proc.returncode, proc.stdout) == (0, "")


# --- commits the gate lets through --------------------------------------------

def test_an_overridden_commit_gets_a_note_and_no_decision():
    proc = _run(HOOK, _event('git commit -m "msg [verify-override: docs only]"'))
    assert json.loads(proc.stdout) == {
        "systemMessage": "⚠ Workspace verify gate OVERRIDDEN: docs only"}


def test_a_commit_with_nothing_staged_gets_no_reply(gate_root):
    hook, _stage, _set = gate_root
    proc = _run(hook, _event('git commit -m "msg"'))
    assert (proc.returncode, proc.stdout) == (0, "")


def test_a_commit_of_only_sec_research_files_gets_a_note_and_no_decision(gate_root):
    hook, stage, set_script_exit = gate_root
    set_script_exit(SCRIPTS[0], 1)  # would deny if the scripts were run
    stage("sec-research/notes.md")
    reply = json.loads(_run(hook, _event('git commit -m "msg"')).stdout)
    assert list(reply) == ["systemMessage"]


def test_a_commit_that_passes_verification_gets_a_note_and_no_decision(gate_root):
    hook, stage, _set = gate_root
    stage("docs/a.md")
    reply = json.loads(_run(hook, _event('git commit -m "msg"')).stdout)
    assert list(reply) == ["systemMessage"]


# --- commits the gate blocks --------------------------------------------------

def test_a_commit_is_denied_when_a_verification_script_fails(gate_root):
    hook, stage, set_script_exit = gate_root
    set_script_exit(SCRIPTS[1], 1)
    stage("docs/a.md")
    reply = json.loads(_run(hook, _event('git commit -m "msg"')).stdout)
    assert reply["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "audit says no" in reply["hookSpecificOutput"]["permissionDecisionReason"]
