# Design: evidence scope-binding PreToolUse hook (D2)

**Date:** 2026-06-25 (form revised during implementation — see History)
**Tracker:** GitHub issue #5 (`GarrettManley/claude-marketplace`); program wave **D2** under epic `hb-28u`.
**Status:** **Shipped** as `evidence@1.2.0` (PR #10). This doc reflects the as-built design.

## Context

The `evidence` plugin ships `scripts/scope_binding.py`, a **scaffold** answering "is this URL/host/path within the loaded engagement scope?" (`check_url`, `check_path`, permissive when no manifest). Nothing *enforced* it: a project had to hand-wire `check_url()` into its own hooks. D2 promotes the scaffold to a ready-made **PreToolUse hook** so a greenfield scoped project (the consumer the README points at — projects without their own framework) gets enforcement without writing one. sec-research and other framework-owning projects keep their own enforcement (per the evidence README's framework-relationship guidance) and simply leave the hook off.

## Decisions (locked)

1. **Gate structured tools only** — tools where the URL/path is an explicit input field. **Skip Bash** (extracting URLs/paths from arbitrary shell text is unreliable).
2. **WebSearch is ungated** — it takes a query, not a URL; no host to bind.
3. **Writes only for paths** — gate `Edit`/`Write`/`MultiEdit`; **Read is ungated** (high-frequency, lower risk; the threat model is egress + writing outside scope).
4. **Separate hook file** `hooks/scope_bind.py`, modeled on `secret_scan.py` — single responsibility, independently testable.
5. **Opt-in via env gate (not enforced globally)** — *revised during implementation.* The hook is registered in the plugin's `hooks.json` **but is a no-op unless `EVIDENCE_SCOPE_ENFORCE` is on AND a manifest is loaded** — the same env-gated opt-in idiom the `learning` plugin uses. So enabling the evidence plugin imposes no enforcement, and a stray `.claude/evidence-scope.yaml` cannot silently activate it. (A pure project-`settings.json` opt-in was rejected: `${CLAUDE_PLUGIN_ROOT}` is not available outside a plugin's own hooks, the install path is version-pinned, and the hook depends on its `scripts/` siblings.)

## Component: `plugins/evidence/hooks/scope_bind.py`

A PreToolUse hook structured like `secret_scan.py`:

1. **`if not _enforcement_enabled(): return 0`** — off unless `EVIDENCE_SCOPE_ENFORCE` ∈ {1,true,on,yes,enabled}.
2. Read JSON payload from stdin → `tool_name`, `tool_input`. Malformed/empty stdin → `return 0`.
3. `sys.path.insert` the plugin `scripts/` dir; import `scope_binding` and (lazily) `evidence_hmac`.
4. `scope = load_scope()`. **If `not scope.is_loaded` → `return 0`** (dormant; no manifest).
5. Dispatch by tool:
   - `WebFetch` → only when the manifest declares `hosts` (`scope.hosts` non-empty): `check_url(url, scope)`. **This is the C2 fix** — `check_url` rejects *all* URLs when `hosts` is empty, so a path-only manifest must not gate `WebFetch` at all.
   - `Edit`/`Write`/`MultiEdit` → `check_path(file_path, scope)` (permissive when the manifest declares no `path_prefixes`).
   - anything else, or a missing `url`/`file_path` → `return 0`.
6. `in_scope` → `return 0`. Out-of-scope → check `redeem_token(EVIDENCE_OVERRIDE_TOKEN, "scope_binding")`: redeemed → stderr notice + `return 0`; else stderr block + `return 2`.

The hook relays `check_url`/`check_path` verdicts and holds no scope logic of its own. Override action is `scope_binding` (distinct from `secret_scan`, per ADR-0004's per-action token design).

## Wiring: `plugins/evidence/hooks/hooks.json`

A **second** `PreToolUse` entry (matcher `WebFetch|Edit|Write|MultiEdit`) runs `scope_bind.py` via `uv run --no-project "${CLAUDE_PLUGIN_ROOT}/hooks/scope_bind.py"`. Because it's the plugin's own hooks.json, `${CLAUDE_PLUGIN_ROOT}` and the `scripts/` siblings resolve. The env gate (Decision 5) keeps it inert until a project opts in.

## Docs

- **ADR-0004** — "scope-binding gate (shipped, opt-in)" section: the env-gated form + why pure settings.json opt-in was rejected.
- **`evidence/README.md`** — `scope_bind.py` in the Hooks table (Active by default: *No — opt-in via `EVIDENCE_SCOPE_ENFORCE`*); the Scope-binding section shows the `EVIDENCE_SCOPE_ENFORCE=on` enable + override flow + the Windows path-prefix caveat; Configuration table gains `EVIDENCE_SCOPE_ENFORCE`.
- **root `SECURITY.md`** — the scope-binding sentence updated to the opt-in hook.

## Testing: `plugins/evidence/tests/test_scope_bind.py`

Drive `main()` with crafted stdin payloads + `EVIDENCE_SCOPE_PATH` → a temp manifest; the fixture strips all `EVIDENCE_*` env (no override leakage) and sets `EVIDENCE_SCOPE_ENFORCE=on` for enforcement cases. 13 tests:

| Case | Manifest | Tool / input | Expect |
|------|----------|--------------|--------|
| Off by default | hosts | WebFetch out-of-scope, `ENFORCE` unset | exit 0 |
| Dormant | none | any tool | exit 0 |
| URL in/out of scope | `hosts:[example.com]` | WebFetch example.com / evil.com | 0 / 2 |
| URL ungated (no hosts) | `path_prefixes` only | WebFetch anything (C2) | exit 0 |
| Path in/out of scope | `path_prefixes:[/eng/]` | Write /eng / /etc | 0 / 2 |
| Writes ungated (no prefixes) | `hosts` only | Write anywhere | exit 0 |
| Not gated | loaded | Bash / WebSearch / Read | exit 0 |
| Override | hosts | out-of-scope + valid `scope_binding` token | exit 0 |
| Wrong-action token | hosts | out-of-scope + `secret_scan` token | exit 2 |
| Malformed stdin | n/a | non-JSON | exit 0 |

## Done bar (met)

`pytest` green (13) · `scope_bind.py` 98% · combined repo coverage 98% · `scripts/verify.sh` all-green · `feat(evidence)` minor bump → `evidence@1.2.0` · `evidence/CHANGELOG.md` + root `CHANGELOG.md` · README/SECURITY/ADR-0004 updated · `claude plugin validate ./plugins/evidence --strict` passes.

## Out of scope (future toggles)

- Best-effort URL/path extraction from **Bash** command text.
- Blocking **WebSearch** entirely while a scope is loaded.
- Gating **Read** against `path_prefixes`.

## History

- Original design: an *enforced global* hook wired unconditionally into `hooks.json`.
- Adversarial review (2026-06-25) challenged the global form (no consumer needs it; sec-research excluded by the README) and caught the C2 `check_url`-rejects-all-when-no-hosts bug. Form changed to **opt-in**.
- During implementation, pure project-`settings.json` opt-in proved infeasible (`${CLAUDE_PLUGIN_ROOT}` / version-pinned path / sibling-import). Settled on the **env-gated registration** (Decision 5) — the `learning`-plugin idiom.
