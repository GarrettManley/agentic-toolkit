# Workspace Hook Federation Router — Design

**Date:** 2026-06-20
**Status:** Design (approved direction; pending spec review → implementation plan)
**Scope:** `C:\Users\Garre\Workspace` (the cross-project hub). Claude-Code-specific infra.

> ⚠️ **Do not publish.** This document names corporate repositories (`Duracell*`, `malachite`)
> as hard-excludes. It must never be surfaced on the public lab site (GEMINI.md §4). Keep it in a
> repo path that the post-commit publish chain does not pick up, or sanitize before any publish.

---

## 1. Problem & Context

`Workspace/` is the primary working directory and the intended **root hub** for cross-project
information, skills, and tooling. Nested projects under it ship their own Claude Code hook suites —
notably `sec-research/`, whose `.claude/settings.json` registers 17 hard-block governance hooks
(PT-1…PT-6, PoT-1…3, S-1/2, UPS-1/2) via four event dispatchers.

Claude Code loads hook configuration from the **launch directory's** project settings (plus user and
local settings), and **does not auto-discover a nested subdirectory's `.claude/settings.json`**.
Consequently, a session launched at the Workspace root runs the Workspace's own hooks (the verify-gate)
but **none of `sec-research/`'s hooks** — silently. Today the only remedy is to relaunch Claude from
inside `sec-research/`, which fights the user's preference to work from the hub.

**Two properties of the nested hooks make a federation layer feasible and safe:**

1. **Self-locating.** `sec-research/hooks/lib/paths.py` computes its root as
   `Path(__file__).resolve().parent.parent.parent` — always `sec-research/`, independent of launch
   dir. All path constants and `is_in_workspace()` derive from it.
2. **Self-gating.** Every dispatcher early-returns `passthrough()` unless the event targets the
   project (`common.py::event_targets_workspace` / `is_in_workspace`). So the hooks are already safe
   to execute on unrelated events — they no-op.

The gap is therefore purely about **discovery and invocation**, not hook logic. Hooks from all loaded
settings sources merge additively, so a parent-registered dispatcher can run alongside the existing
verify-gate.

## 2. Goals / Non-Goals

**Goals**
- Nested-project Claude hooks fire correctly when Claude is launched at the Workspace root.
- Standalone launches (Claude started inside a nested project) keep working **unchanged**.
- Generic: any nested project that ships a `.claude/settings.json` is federated automatically — no
  per-project router code.
- Faithful hook protocol: event JSON, matchers, `${CLAUDE_PROJECT_DIR}`, exit codes, and stdout
  context propagate exactly as if the child hook had been invoked natively.
- Corporate repos (`Duracell*`, `malachite`) are structurally excluded.

**Non-Goals**
- Replacing or modifying any nested project's hook logic (the router is content-agnostic).
- Federating git hooks (`.git/hooks/*`) — those already fire on commit/push regardless of launch dir.
- Cross-machine/remote behavior; this is a local-launch concern.
- Deep (recursive) discovery beyond depth-1 children (YAGNI; revisit if a real nested-nested case appears).

## 3. Architecture Overview

A single parent-level dispatcher script is registered in `Workspace/.claude/settings.json` for all four
Claude hook events. On each event it:

```
stdin(event JSON) ─▶ hook_router.py
                       │ 1. parse event; read hook_event_name, tool_name
                       │ 2. discover_projects()  (depth-1 scan, excludes, signature-cached)
                       │ 3. for each project, for each hook entry for this event:
                       │       if matcher matches tool_name:
                       │          resolve_command(${CLAUDE_PROJECT_DIR} → child dir)
                       │          run_child_hook(cmd, env, stdin=event bytes)
                       │ 4. aggregate(results) per event semantics
                       ▼
              exit code + stderr/stdout  (faithful to the blocking child)
```

The child's own `.claude/settings.json` is the **source of truth** — no new manifest format. This is
why standalone launches are unaffected (the child loads it natively) and why federation needs zero
per-project code.

## 4. Components

| File | Responsibility |
|---|---|
| `.claude/hooks/hook_router.py` | Entry point for all 4 events; self-dispatches on `hook_event_name`; orchestrates discover → match → run → aggregate; owns exit-code/stdout fidelity and fail-open behavior. |
| `.claude/hooks/hook_router_lib.py` | Pure, unit-testable functions: `discover_projects(root, config)`, `matcher_matches(matcher, tool_name)`, `resolve_command(cmd, child_dir)`, `run_child_hook(cmd, env, stdin_bytes, timeout)`, `aggregate(event_name, child_results)`. No global side effects. |
| `.claude/hooks/hook-router.config.json` | User-tunable: `enabled` (bool), `ignore` (extra dir names/globs), `matchers` (per-event override), `timeout_seconds`. **Corporate excludes live in code, not here.** |
| `.claude/.hook-router-cache.json` | Gitignored. Cached discovery: `{signature, projects:[{dir, settings_path}]}`. |
| `.claude/hooks/tests/test_hook_router.py` | pytest suite (stub child-hooks). |

Stdlib-only (no third-party imports) so the router stays fast to start and dependency-free, since it
spawns on every tool call under the chosen broad `.*` matcher.

## 5. Discovery (scan + exclude-list)

- Scan **depth-1** children of `${CLAUDE_PROJECT_DIR}`; a child qualifies if `<child>/.claude/settings.json` exists.
- **Hard-coded safety excludes (non-overridable constants in code):** any dir matching `Duracell*`, or named `malachite`. The router does not stat, read, or invoke anything beneath these.
- **User excludes:** `config.ignore` (dir names or globs).
- **Caching:** compute a `signature` = sorted list of `(child_name, mtime_of_its_settings.json)`. Cache the resolved project list keyed by signature; on each event, cheaply re-stat depth-1 children and rebuild only when the signature changes. (Cache miss/error ⇒ live scan; never fatal.)

## 6. Event Routing & Exit-Code Fidelity

The event JSON is read from stdin **once** (single-read) and its raw bytes are replayed to each child.
For each discovered project and each hook entry registered for `hook_event_name` whose `matcher`
regex matches `tool_name` (absent matcher ⇒ always match):

1. **Resolve command:** literal-substitute `${CLAUDE_PROJECT_DIR}` → child's absolute dir in the
   command string, **and** set `CLAUDE_PROJECT_DIR=<child dir>` in the child's environment (covers both
   expansion styles). Other env is inherited.
2. **Run child:** `subprocess.run(cmd, input=event_bytes, capture_output=True, timeout=...)`.
3. **Aggregate**, per event:

| Event | Block signal | Aggregation |
|---|---|---|
| `PreToolUse` | child exit `2` (or stdout deny JSON) | **short-circuit** on first block → router exits `2`, forwards that child's stderr verbatim |
| `PostToolUse` | child exit `2` | run all matching; if any exit `2`, exit `2` and forward its stderr |
| `Stop` / `SubagentStop` | child exit `2` ("don't stop") | run all; propagate first block |
| `UserPromptSubmit` | child exit `2` | run all; **concatenate** children stdout (injected context) to router stdout; propagate any block |

- **Non-2 non-zero** from a child (it crashed) ⇒ forward as a **non-blocking** error (surface stderr, exit 0 for the router's own decision) — never silently swallowed.
- **Fail-open on router faults:** any exception in discovery/orchestration ⇒ router exits `0` (pass-through). The router must never block normal Workspace work because of its own bug. It only ever blocks when a child *deliberately* returns exit `2`. (This asymmetry is load-bearing: fail-closed on a router bug would brick the whole hub; swallowing a child's exit-2 would silently defeat the child's guarantees.)

## 7. Registration & Performance

Registered in the **committed** `Workspace/.claude/settings.json`, additive to the existing
verify-gate, for `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`, each with matcher `.*`
(broad — chosen for maximum generality so any future nested project's tool interest is covered with
zero config).

Cost: one router process spawn per tool call. Mitigations baked into the design:
- **Stdlib-only, lazy imports**, minimal startup.
- **Signature-cached discovery** (a few `stat`s on the no-op path, no re-parse).
- **Fast pre-checks** before spawning any child: skip projects with no hook entry for this event; skip
  entries whose matcher doesn't match `tool_name`. A child subprocess spawns only when it would
  genuinely run natively.

## 8. No-Double-Fire & Interaction

- **Standalone launch (inside child):** parent `Workspace/.claude/settings.json` is not loaded; only the
  child's native hooks run. Router absent. ✓
- **Hub launch (Workspace root):** child's settings not loaded by Claude; the router replays them. Each
  child hook fires exactly once. ✓
- **Verify-gate** (`check_verify_before_commit.py`, matcher `Bash|PowerShell`) remains a separate native
  hook; unaffected. **Git hooks** (G-1/2/4) fire on commit/push regardless. The router governs only the
  four Claude events.

## 9. Config Schema (`hook-router.config.json`)

```json
{
  "enabled": true,
  "ignore": [],
  "matchers": { "PreToolUse": ".*", "PostToolUse": ".*", "Stop": ".*", "UserPromptSubmit": ".*" },
  "timeout_seconds": 15
}
```
`matchers` here documents/echoes what's registered in `settings.json` (the registration is what Claude
actually honors); `ignore` adds to the hard-coded corporate excludes; `enabled:false` makes the router a
no-op pass-through (kill switch).

## 10. Testing

`pytest` (`.claude/hooks/tests/test_hook_router.py`), stub child hooks = tiny scripts that exit 0/2 or
emit stdout:
- **Discovery:** finds a stub child; **excludes** a `Duracell-x/` and `malachite/` stub even with a
  `.claude/settings.json`; honors `config.ignore`.
- **Matcher:** `matcher_matches("Edit|Write", "Edit")` true; `"Bash"` false; absent matcher always true.
- **Command resolution:** `${CLAUDE_PROJECT_DIR}` rewritten to the child dir; env set.
- **Routing/exit codes:** child exit 2 ⇒ router exit 2 + child stderr forwarded; child exit 0 ⇒ router 0;
  child crash (exit 1) ⇒ router 0 + stderr surfaced (non-blocking).
- **UserPromptSubmit:** two children's stdout concatenated onto router stdout.
- **stdin replay:** child receives the exact event bytes.
- **Fail-open:** a malformed cache / unreadable child settings ⇒ router exits 0, does not raise.
- **End-to-end (manual/integration):** from Workspace root, an `Edit` to a `sec-research/programs/...`
  path triggers PT-3 (block); an `Edit` to `site/content/...` passes.

## 11. Risks & Open Questions

- **Per-event spawn latency** (broad `.*`): accepted by decision. If sessions feel slow, narrow the
  registered matcher in `settings.json` (config documents the intended set) — no code change.
- **stdout-decision hooks:** current children (sec-research) block via exit-2 + stderr, not stdout JSON.
  The router supports both, but exit-2 is the tested path; stdout-deny handling is best-effort until a
  child uses it.
- **Windows path/shell quoting:** child commands use `python ${CLAUDE_PROJECT_DIR}/.../x.py` with forward
  slashes (the established convention; backslash-then-alpha is shell-mangled). Router substitutes with
  forward slashes and runs via `subprocess.run` with a parsed argv (no shell) where feasible.
- **Spec publish hazard:** this file names corporate repos; it must not be committed to a path the
  publish chain (`site/`, `.ai/`, `docs/`, `README.md` gate) ships to the public site. Resolve the
  publish-safe location at commit time.

## 12. Decisions Log

- **Scope:** auto-discovery router (vs. one-off hoist / opt-in marker / central registry).
- **Discovery:** scan depth-1 + hard-coded corporate excludes + user ignore-list.
- **Source of truth:** child's existing `.claude/settings.json` (no new manifest).
- **Matcher:** broad `.*` for generality (offset by a cheap router).
- **Config home:** committed `Workspace/.claude/settings.json` + committed `hook-router.config.json`.
- **Safety:** fail-open on router faults; fail-closed only on a child's deliberate exit-2.
