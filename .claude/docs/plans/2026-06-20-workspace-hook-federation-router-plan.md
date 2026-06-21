# Workspace Hook Federation Router — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parent-level Claude hook dispatcher (`.claude/hooks/hook_router.py`) that auto-discovers nested projects' own `.claude/settings.json` and replays their hooks from the Workspace root, so nested-project hooks (e.g. sec-research's 17 governance hooks) fire without relaunching Claude inside the subdir.

**Architecture:** One entry script registered for all four Claude hook events; it self-dispatches on `hook_event_name`. A pure-function library (`hook_router_lib.py`) does discovery (depth-1 scan, corporate-repo hard-excludes), matcher evaluation, `${CLAUDE_PROJECT_DIR}` rewriting, child invocation with single-read stdin replay, and per-event exit-code aggregation. The child's existing settings file is the source of truth — no new manifest, and standalone launches are unaffected.

**Tech Stack:** Python 3.14 **stdlib only** (`subprocess`, `json`, `re`, `shlex`, `fnmatch`, `pathlib`, `dataclasses`), `pytest` for tests. No third-party imports (the router spawns on every tool call; startup must be cheap and dependency-free).

## Context

`Workspace/` is the primary working directory and intended root hub for cross-project tooling. Claude Code loads hooks from the launch dir's project settings and does **not** auto-discover a nested subdir's `.claude/settings.json` — so a root-launched session runs none of `sec-research/`'s hooks, silently. The nested hooks are already **self-locating** (`paths.py` computes its own root) and **self-gating** (`event_targets_workspace` no-ops on unrelated events), so they are safe to execute on any event; the only gap is discovery+invocation. Hooks from all loaded settings sources merge additively, so a parent-registered dispatcher coexists with the existing verify-gate.

Design spec: `.claude/docs/specs/2026-06-20-workspace-hook-federation-router-design.md`. Tracker: `hb-ry9`.

**Refinement vs. spec:** the spec proposed a signature cache for discovery. On analysis, the depth-1 scan (~10 dirs, a handful of `stat`s) is sub-millisecond and the dominant per-event cost is the router *process spawn* (uncacheable). So v1 scans directly and omits the cache — revisit only if profiling shows the scan itself matters. (This removes the cache file and a `.gitignore` change.)

## Global Constraints

- **Stdlib only.** No `requests`/`pyyaml`/etc. Keep imports minimal and lazy where reasonable for fast startup.
- **Corporate excludes are hard-coded, non-overridable constants:** `Duracell*` (glob) and `malachite`. The router must never `stat`, read, or invoke anything under a child dir matching these — independent of config. This enforces the workspace's corporate-isolation policy in code.
- **Fail-open on router faults; fail-closed only on a child's deliberate exit-2.** Any exception in the router's own discovery/orchestration ⇒ exit `0` (pass-through). The router must never block normal Workspace work due to its own bug. It blocks (exit `2`) only when a child hook deliberately returns exit `2`, and then it forwards that child's stderr verbatim.
- **Single-read stdin.** Read the event bytes once (`sys.stdin.buffer.read()`); replay the same bytes to every child's stdin.
- **`${CLAUDE_PROJECT_DIR}` rewriting:** in each child command, literal-substitute `${CLAUDE_PROJECT_DIR}` → that child's absolute dir (forward-slash form), and set `CLAUDE_PROJECT_DIR=<child dir>` in the child's env.
- **Windows path handling:** child commands use forward slashes by convention; parse with `shlex.split(cmd, posix=True)` (no backslash-eating, no shell). Set child `cwd` to the child dir.
- **No double-fire:** standalone launch loads only the child's native hooks; hub launch loads only the router (which replays them). Each child hook fires exactly once per scenario. The router governs only the four Claude events — git hooks (G-1/2/4) and the verify-gate are untouched.
- **Commits live under `.claude/`** — tracked (allow-listed in `.gitignore`) and NOT matched by the post-commit publish gate (`site/|.ai/|docs/|README.md`), so no Firebase deploy fires. Stage only router files per commit. Run tests before each commit.

---

## File Structure

**Create:**
- `.claude/hooks/hook_router_lib.py` — pure functions: `load_config`, `discover_projects`, `matcher_matches`, `resolve_command`, `run_child_hook`, `aggregate`, `route_event`. The `Project` dataclass. All logic testable without touching real settings or `sys.exit`.
- `.claude/hooks/hook_router.py` — thin I/O entry: reads stdin, loads config, calls `route_event`, writes stdout/stderr, `sys.exit(rc)`; top-level `try/except` → exit 0 (fail-open).
- `.claude/hooks/hook-router.config.json` — `{enabled, ignore, timeout_seconds}`.
- `.claude/hooks/tests/conftest.py` — puts `.claude/hooks/` on `sys.path`; provides stub-child-project fixtures.
- `.claude/hooks/tests/test_hook_router.py` — the suite.
- `.claude/hooks/tests/stubs/` — tiny stub child-hook scripts (`pass_hook.py`, `block_hook.py`, `echo_hook.py`, `crash_hook.py`).

**Modify:**
- `.claude/settings.json` — register the router for `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit` (additive to the existing verify-gate entry).

---

## Task 0: Library scaffolding — config + discovery

**Files:**
- Create: `.claude/hooks/hook_router_lib.py`
- Create: `.claude/hooks/hook-router.config.json`
- Create: `.claude/hooks/tests/conftest.py`
- Create: `.claude/hooks/tests/test_hook_router.py`

**Interfaces:**
- Produces: `load_config(path: Path) -> dict` (defaults `{enabled:True, ignore:[], timeout_seconds:15}` if missing/unreadable). `Project` dataclass `(dir: Path, settings: dict)`. `discover_projects(root: Path, config: dict) -> list[Project]`.
- Constant: `HARD_EXCLUDES = ("Duracell*", "malachite")`.

- [ ] **Step 1: Write the conftest fixture**

`.claude/hooks/tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Write the failing discovery tests**

Append to `.claude/hooks/tests/test_hook_router.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -v`
Expected: FAIL (`No module named 'hook_router_lib'`). (If `pytest` isn't on the base interpreter, use `uvx pytest .claude/hooks/tests/ -v`.)

- [ ] **Step 4: Implement config + discovery in `hook_router_lib.py`**

```python
"""Pure functions for the Workspace hook federation router. No sys.exit, no global I/O
beyond reading child settings/config. Unit-testable in isolation."""
from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path

# Corporate-isolation policy, enforced in code (NOT user-overridable).
HARD_EXCLUDES: tuple[str, ...] = ("Duracell*", "malachite")

_DEFAULT_CONFIG = {"enabled": True, "ignore": [], "timeout_seconds": 15}


@dataclass(frozen=True)
class Project:
    dir: Path
    settings: dict


def load_config(path: Path) -> dict:
    """Read the router config, falling back to defaults on missing/invalid file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_DEFAULT_CONFIG)
    return {**_DEFAULT_CONFIG, **(data if isinstance(data, dict) else {})}


def _excluded(name: str, user_ignore: list[str]) -> bool:
    if any(fnmatch.fnmatch(name, pat) for pat in HARD_EXCLUDES):
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in user_ignore)


def discover_projects(root: Path, config: dict) -> list[Project]:
    """Depth-1 scan for <child>/.claude/settings.json, minus corporate + user excludes."""
    user_ignore = config.get("ignore", []) or []
    projects: list[Project] = []
    try:
        children = sorted(p for p in Path(root).iterdir() if p.is_dir())
    except OSError:
        return projects
    for child in children:
        if _excluded(child.name, user_ignore):
            continue
        settings_path = child / ".claude" / "settings.json"
        if not settings_path.is_file():
            continue
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # a child with broken settings is skipped, not fatal
        projects.append(Project(dir=child, settings=settings))
    return projects
```

- [ ] **Step 5: Create the config file**

`.claude/hooks/hook-router.config.json`:

```json
{
  "enabled": true,
  "ignore": [],
  "timeout_seconds": 15
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -v`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
git add .claude/hooks/hook_router_lib.py .claude/hooks/hook-router.config.json .claude/hooks/tests/
git commit -m "feat(hooks): router discovery + config (corporate hard-excludes)"
```

---

## Task 1: Matcher evaluation + command resolution

**Files:**
- Modify: `.claude/hooks/hook_router_lib.py`
- Modify: `.claude/hooks/tests/test_hook_router.py`

**Interfaces:**
- Produces: `matcher_matches(matcher: str | None, tool_name: str) -> bool`. `resolve_command(command: str, child_dir: Path) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "matcher or resolve" -v`
Expected: FAIL (`AttributeError: ... has no attribute 'matcher_matches'`).

- [ ] **Step 3: Implement**

Add to `hook_router_lib.py`:

```python
import re
import shlex


def matcher_matches(matcher: str | None, tool_name: str) -> bool:
    """Claude matchers are regexes over tool_name. Empty / '*' / '.*' mean match-all.
    A malformed regex matches nothing (and is the child's config bug, not ours)."""
    if not matcher or matcher in ("*", ".*"):
        return True
    try:
        return re.search(matcher, tool_name) is not None
    except re.error:
        return False


def resolve_command(command: str, child_dir: Path) -> list[str]:
    """Substitute ${CLAUDE_PROJECT_DIR} -> child dir (forward slashes) and split to argv.
    posix=True is correct here because commands use forward slashes by convention."""
    substituted = command.replace("${CLAUDE_PROJECT_DIR}", Path(child_dir).as_posix())
    return shlex.split(substituted, posix=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "matcher or resolve" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/hook_router_lib.py .claude/hooks/tests/test_hook_router.py
git commit -m "feat(hooks): router matcher eval + command resolution"
```

---

## Task 2: Child invocation with stdin replay

**Files:**
- Modify: `.claude/hooks/hook_router_lib.py`
- Create: `.claude/hooks/tests/stubs/echo_hook.py`, `.claude/hooks/tests/stubs/block_hook.py`, `.claude/hooks/tests/stubs/crash_hook.py`
- Modify: `.claude/hooks/tests/test_hook_router.py`

**Interfaces:**
- Produces: `run_child_hook(argv: list[str], child_dir: Path, stdin_bytes: bytes, timeout: float) -> tuple[int, str, str]` (rc, stdout, stderr). Sets `CLAUDE_PROJECT_DIR` env + `cwd` to child dir. Timeout/spawn failure ⇒ `(0, "", "<diagnostic>")` (fail-open, non-blocking).

- [ ] **Step 1: Create the stub child hooks**

`.claude/hooks/tests/stubs/echo_hook.py`:

```python
import sys
data = sys.stdin.buffer.read().decode("utf-8", "replace")
import os
sys.stdout.write(f"echo:len={len(data)}:cpd={os.environ.get('CLAUDE_PROJECT_DIR','')}")
sys.exit(0)
```

`.claude/hooks/tests/stubs/block_hook.py`:

```python
import sys
sys.stdin.buffer.read()
sys.stderr.write('{"rule_id":"STUB","action":"block","reason":"stub block"}')
sys.exit(2)
```

`.claude/hooks/tests/stubs/crash_hook.py`:

```python
import sys
sys.stdin.buffer.read()
sys.stderr.write("stub crashed")
sys.exit(1)
```

- [ ] **Step 2: Write the failing tests**

```python
import sys
from pathlib import Path

STUBS = Path(__file__).resolve().parent / "stubs"


def test_run_child_replays_stdin_and_sets_env(tmp_path):
    import hook_router_lib as lib
    child = tmp_path / "proj"; child.mkdir()
    argv = [sys.executable, str(STUBS / "echo_hook.py")]
    rc, out, err = lib.run_child_hook(argv, child, b'{"hook_event_name":"PreToolUse"}', 15)
    assert rc == 0
    assert "echo:len=31" in out                      # exact bytes were replayed to stdin
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
```

> Note: `echo:len=31` assumes the stdin payload `{"hook_event_name":"PreToolUse"}` is 31 bytes — count it when writing the test; adjust the literal to the actual length.

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "run_child" -v`
Expected: FAIL (no attribute `run_child_hook`).

- [ ] **Step 4: Implement**

Add to `hook_router_lib.py`:

```python
import os
import subprocess


def run_child_hook(argv: list[str], child_dir: Path, stdin_bytes: bytes,
                   timeout: float) -> tuple[int, str, str]:
    """Invoke one child hook with the replayed event on stdin. Returns (rc, stdout, stderr).
    Spawn failure / timeout is fail-open (rc 0) with a diagnostic on stderr — a router-side
    fault must not block the user's action; only a child's deliberate exit-2 blocks."""
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(child_dir)}
    try:
        proc = subprocess.run(argv, input=stdin_bytes, capture_output=True,
                              env=env, cwd=str(child_dir), timeout=timeout)
    except FileNotFoundError as e:
        return 0, "", f"[hook_router] child not runnable {argv!r}: {e}\n"
    except subprocess.TimeoutExpired:
        return 0, "", f"[hook_router] child timed out ({timeout}s): {argv!r}\n"
    except OSError as e:
        return 0, "", f"[hook_router] child spawn error {argv!r}: {e}\n"
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "run_child" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/hooks/hook_router_lib.py .claude/hooks/tests/
git commit -m "feat(hooks): router child invocation + stdin replay (fail-open spawn)"
```

---

## Task 3: Aggregation + route_event orchestration

**Files:**
- Modify: `.claude/hooks/hook_router_lib.py`
- Modify: `.claude/hooks/tests/test_hook_router.py`

**Interfaces:**
- Produces: `aggregate(event_name: str, results: list[tuple[int,str,str]]) -> tuple[int,str,str]`. `route_event(stdin_bytes: bytes, root: Path, config: dict) -> tuple[int,str,str]` (parses event, discovers, matches, runs children, short-circuits on first exit-2, else aggregates; parse failure ⇒ `(0,"","")`).

- [ ] **Step 1: Write the failing tests**

```python
import json
import sys
from pathlib import Path

STUBS = Path(__file__).resolve().parent / "stubs"


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
    cmd = f"{sys.executable} {STUBS / 'block_hook.py'}"
    mk("sec-research", {"PreToolUse": [{"matcher": ".*", "hooks": [{"command": cmd}]}]})
    event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"}).encode()
    rc, out, err = lib.route_event(event, root, lib.load_config(root / "x.json"))
    assert rc == 2 and "stub block" in err


def test_route_event_passes_when_matcher_excludes(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    cmd = f"{sys.executable} {STUBS / 'block_hook.py'}"
    mk("sec-research", {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": cmd}]}]})
    event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"}).encode()
    rc, out, err = lib.route_event(event, root, lib.load_config(root / "x.json"))
    assert rc == 0  # blocker's matcher (Bash) didn't match tool_name Edit -> never invoked


def test_route_event_userpromptsubmit_concats_stdout(fake_root):
    import hook_router_lib as lib
    root, mk = fake_root
    cmd = f"{sys.executable} {STUBS / 'echo_hook.py'}"
    mk("a", {"UserPromptSubmit": [{"hooks": [{"command": cmd}]}]})
    mk("b", {"UserPromptSubmit": [{"hooks": [{"command": cmd}]}]})
    event = json.dumps({"hook_event_name": "UserPromptSubmit"}).encode()
    rc, out, err = lib.route_event(event, root, lib.load_config(root / "x.json"))
    assert rc == 0 and out.count("echo:") == 2


def test_route_event_unparseable_is_fail_open(fake_root):
    import hook_router_lib as lib
    root, _ = fake_root
    rc, out, err = lib.route_event(b"not json", root, lib.load_config(root / "x.json"))
    assert rc == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "aggregate or route_event" -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add to `hook_router_lib.py`:

```python
def aggregate(event_name: str, results: list[tuple[int, str, str]]) -> tuple[int, str, str]:
    """First child exit-2 blocks (forward its stderr). Otherwise exit 0; concatenate all
    child stdout (e.g. UserPromptSubmit injected context) and non-empty stderr (diagnostics)."""
    for rc, _out, err in results:
        if rc == 2:
            return 2, "", err
    out = "".join(r[1] for r in results)
    err = "".join(r[2] for r in results if r[2])
    return 0, out, err


def route_event(stdin_bytes: bytes, root: Path, config: dict) -> tuple[int, str, str]:
    """Parse the event, fan out to matching child hooks, short-circuit on first block."""
    try:
        event = json.loads(stdin_bytes.decode("utf-8")) if stdin_bytes.strip() else {}
    except (ValueError, UnicodeDecodeError):
        return 0, "", ""  # can't parse -> fail open
    event_name = event.get("hook_event_name", "")
    tool_name = event.get("tool_name", "")
    timeout = config.get("timeout_seconds", 15)

    results: list[tuple[int, str, str]] = []
    for proj in discover_projects(root, config):
        for entry in (proj.settings.get("hooks", {}).get(event_name) or []):
            if not matcher_matches(entry.get("matcher"), tool_name):
                continue
            for h in (entry.get("hooks") or []):
                command = h.get("command")
                if not command:
                    continue
                argv = resolve_command(command, proj.dir)
                rc, out, err = run_child_hook(argv, proj.dir, stdin_bytes, timeout)
                results.append((rc, out, err))
                if rc == 2:
                    return 2, "", err  # short-circuit: a block is terminal
    return aggregate(event_name, results)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "aggregate or route_event" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/hook_router_lib.py .claude/hooks/tests/test_hook_router.py
git commit -m "feat(hooks): router event aggregation + route_event orchestration"
```

---

## Task 4: Entry script (`hook_router.py`)

**Files:**
- Create: `.claude/hooks/hook_router.py`
- Modify: `.claude/hooks/tests/test_hook_router.py`

**Interfaces:**
- Produces: `main() -> int` (reads stdin bytes, resolves `ROOT = Path(__file__).resolve().parents[1].parent` i.e. Workspace, loads `hook-router.config.json`, calls `route_event`, writes stdout/stderr, returns rc; any uncaught exception ⇒ return 0). Invoked for all four events.

- [ ] **Step 1: Write the failing CLI integration test**

```python
import json
import subprocess
import sys
from pathlib import Path

ROUTER = Path(__file__).resolve().parents[1] / "hook_router.py"  # .claude/hooks/hook_router.py


def test_cli_passes_through_with_no_projects(tmp_path):
    """Running the router from a root with no federated projects exits 0 and writes nothing fatal."""
    event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read"})
    proc = subprocess.run([sys.executable, str(ROUTER)], input=event.encode(),
                          capture_output=True, cwd=str(tmp_path),
                          env={"CLAUDE_PROJECT_DIR": str(tmp_path), **_min_env()})
    assert proc.returncode == 0


def _min_env():
    import os
    return {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
```

> The router resolves its scan root from its own location (`parents[...]` to Workspace), so this test exercises the real entry path; with `cwd`/`CLAUDE_PROJECT_DIR` = an empty tmp dir there are no children to federate, and we assert clean pass-through. A block-path integration test is covered by `route_event` tests in Task 3.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest .claude/hooks/tests/test_hook_router.py -k "cli" -v`
Expected: FAIL (router file does not exist).

- [ ] **Step 3: Implement `.claude/hooks/hook_router.py`**

```python
#!/usr/bin/env python
"""Workspace hook federation router.

Registered for PreToolUse / PostToolUse / Stop / UserPromptSubmit at the Workspace root.
Self-dispatches on hook_event_name, discovers nested projects' own .claude/settings.json,
and replays their matching hooks — so nested-project hooks fire from the hub root.

Fail-open on any router fault; only a child's deliberate exit-2 blocks (its stderr is
forwarded verbatim)."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent           # .claude/hooks/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import hook_router_lib as lib  # noqa: E402

ROOT = _HERE.parent.parent                          # .claude/hooks -> .claude -> Workspace
CONFIG_PATH = _HERE / "hook-router.config.json"


def main() -> int:
    raw = sys.stdin.buffer.read()
    try:
        config = lib.load_config(CONFIG_PATH)
        if not config.get("enabled", True):
            return 0
        rc, out, err = lib.route_event(raw, ROOT, config)
        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        return rc
    except Exception as exc:                        # noqa: BLE001 — fail-open is the contract
        sys.stderr.write(f"[hook_router] internal error (passing through): {exc}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the CLI test + full suite**

Run: `python -m pytest .claude/hooks/tests/ -v`
Expected: PASS (all tasks' tests).

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/hook_router.py .claude/hooks/tests/test_hook_router.py
git commit -m "feat(hooks): router entry script (self-dispatch + fail-open)"
```

---

## Task 5: Register the router + end-to-end verification + docs

**Files:**
- Modify: `.claude/settings.json`
- Modify: `CLAUDE.md` (note the federation behavior)
- Modify: `.claude/docs/specs/2026-06-20-workspace-hook-federation-router-design.md` (mark the cache-omission refinement, status → implemented)

- [ ] **Step 1: Register the router in `.claude/settings.json`**

Add four entries (keep the existing verify-gate `PreToolUse` entry — append the router entry to the `PreToolUse` array):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/check_verify_before_commit.py\"", "timeout": 30 }
        ]
      },
      {
        "matcher": ".*",
        "hooks": [
          { "type": "command", "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/hook_router.py\"", "timeout": 20 }
        ]
      }
    ],
    "PostToolUse": [
      { "matcher": ".*", "hooks": [ { "type": "command", "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/hook_router.py\"", "timeout": 20 } ] }
    ],
    "Stop": [
      { "matcher": ".*", "hooks": [ { "type": "command", "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/hook_router.py\"", "timeout": 20 } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/hook_router.py\"", "timeout": 20 } ] }
    ]
  }
}
```

> Preserve the existing top-level keys/comments in `.claude/settings.json` (e.g. `permissions`, `$comment`); only add to `hooks`. The router command uses double-quotes around the substituted path (it contains no spaces, but quoting is consistent with the verify-gate entry).

- [ ] **Step 2: End-to-end verification (manual, from the Workspace root)**

Restart the Claude session at the Workspace root so the new settings load. Then:

1. **Federation fires for sec-research:** attempt an `Edit`/`Write` to a path under `sec-research/` that is outside any loaded scope context but should trip a sec-research rule — e.g. ask Claude to write to `sec-research/programs/__router_probe__/scope.yaml` with an out-of-scope shape, OR more simply, run a `Bash` command containing a clearly out-of-scope `curl https://example.invalid` *with* "sec-research" in the command so PT-1 evaluates it. Expect the router to surface a `PT-1` block (JSON on stderr) — proving sec-research's PreToolUse ran via the router.
2. **No false block for non-sec-research work:** `Edit` a file under `site/content/...`. Expect it to pass (sec-research's `is_in_workspace` returns False ⇒ passthrough ⇒ router aggregates exit 0).
3. **No double-fire / standalone intact:** launch a session *inside* `sec-research/` and confirm the same `PT-1` behavior via its native hooks (the router is absent there).

Document the observed outputs in the retrospective.

- [ ] **Step 3: Note the behavior in `CLAUDE.md`**

Under the "Claude Code session hooks" section, add a bullet:

```markdown
- `PreToolUse|PostToolUse|Stop|UserPromptSubmit` → `.claude/hooks/hook_router.py` (federation router): auto-discovers nested projects' own `.claude/settings.json` (depth-1; `Duracell*`/`malachite` hard-excluded) and replays their hooks from this root, so e.g. `sec-research/`'s governance hooks fire without relaunching Claude inside the subdir. Config: `.claude/hooks/hook-router.config.json` (`enabled` kill-switch, `ignore` list, `timeout_seconds`). Fail-open on router faults; a child's exit-2 still blocks. See `.claude/docs/specs/2026-06-20-workspace-hook-federation-router-design.md`.
```

- [ ] **Step 4: Run the full suite once more, then commit**

Run: `python -m pytest .claude/hooks/tests/ -v`
Expected: PASS.

```bash
git add .claude/settings.json CLAUDE.md .claude/docs/specs/2026-06-20-workspace-hook-federation-router-design.md
git commit -m "feat(hooks): register federation router for all 4 events + docs (hb-ry9)"
```

---

## Verification

**1. Unit suite (offline):**
```bash
cd C:/Users/Garre/Workspace
python -m pytest .claude/hooks/tests/ -v      # or: uvx pytest .claude/hooks/tests/ -v
```
Expected: all green — discovery (incl. corporate exclusion), matcher, command resolution, stdin replay, fail-open spawn, aggregation, route_event short-circuit + concat, CLI pass-through.

**2. Corporate-exclusion assertion** is covered by `test_discover_excludes_corporate_repos` — a `Duracell-*` / `malachite` child with a `.claude/settings.json` is never federated. This is the load-bearing safety test; it must pass.

**3. Live federation (manual, Task 5 Step 2):** from the Workspace root, a sec-research-targeting action trips a sec-research rule via the router; a `site/` action passes; standalone sec-research launch behaves identically. 

**4. No-deploy check:** every commit in this plan stages only `.claude/` paths, so the post-commit hook prints "no publish-relevant paths — skipping site deploy." Confirm that line appears (no Firebase deploy).

---

## Retrospective

_(Filled in after implementation via the retrospective skill.)_

**Issue state:** Closes hb-ry9 (Workspace hook federation router). Follow-ups → new beads / `Follows up hb-ry9`.

- **What worked:**
- **Friction / surprises** (esp. Claude hook-merge behavior, `${CLAUDE_PROJECT_DIR}` resolution, shlex on Windows paths):
- **Live federation result** (did sec-research's PT-1 fire from the root? false-block on `site/`?):
- **Follow-ups discovered** (e.g. stdout-deny JSON children, narrowing the matcher if startup latency bites, a signature cache if depth-1 scan ever matters, generalizing to depth>1):
