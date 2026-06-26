# Design: evidence scope-binding PreToolUse hook (D2)

**Date:** 2026-06-25
**Tracker:** GitHub issue #5 (`GarrettManley/claude-marketplace`); program wave **D2** under epic `hb-28u`.
**Status:** Approved design — ready for implementation plan.

## Context

The `evidence` plugin ships `scripts/scope_binding.py`, a **scaffold** that answers "is this URL/host/path within the loaded engagement scope?" (`check_url`, `check_path`, permissive when no manifest). But nothing *enforces* it: a project must hand-wire `check_url()` calls into its own hooks. ADR-0004 already references a "future `scope_binding` gate." D2 promotes the scaffold to a real **PreToolUse hook** so scope-binding is enforced automatically, modeled on the existing `secret_scan.py` hook — including its HMAC override valve.

This matters for the sec-research workflow (and any scoped engagement): network egress and file writes should be confined to the declared target without per-project hook wiring.

## Decisions (locked)

1. **Gate structured tools only** — tools where the URL/path is an explicit input field. **Skip Bash** (extracting URLs/paths from arbitrary shell text is unreliable; documented as a known gap).
2. **WebSearch is ungated** — it takes a query, not a URL, so there is no host to bind.
3. **Writes only for paths** — gate `Edit`/`Write`/`MultiEdit`; **Read is ungated** (high-frequency, lower risk; the threat model is egress + writing outside scope).
4. **Separate hook file** `hooks/scope_bind.py`, mirroring `secret_scan.py` — single responsibility, independently testable and disable-able. (Rejected: folding into `secret_scan.py`; a generic multi-check guard — premature.)

## Component: `plugins/evidence/hooks/scope_bind.py`

A PreToolUse hook structured exactly like `secret_scan.py`:

1. Read JSON payload from stdin → `tool_name`, `tool_input`. Malformed/empty stdin → `return 0`.
2. `sys.path.insert` the plugin `scripts/` dir; import `scope_binding` and (lazily) `evidence_hmac`.
3. `scope = scope_binding.load_scope()`. **If `not scope.is_loaded` → `return 0`** (permissive no-op; the hook is dormant until a project drops `.claude/evidence-scope.yaml`).
4. Dispatch by tool:
   - `WebFetch` → `in_scope, reason = check_url(tool_input["url"], scope)`
   - `Edit` / `Write` / `MultiEdit` → `in_scope, reason = check_path(tool_input["file_path"], scope)`
   - anything else → `return 0` (not gated)
   - A missing `url`/`file_path` field → `return 0` (nothing to check).
5. `in_scope` → `return 0`. Out-of-scope → check `redeem_token(EVIDENCE_OVERRIDE_TOKEN, "scope_binding")`:
   - redeemed → stderr notice, `return 0`
   - else → stderr block message (the checker's `reason` + how to issue a `scope_binding` override token) + `return 2`.

The hook relays `check_url`/`check_path` verdicts verbatim and holds **no scope logic of its own**. Manifest contents govern strictness (`check_path` is permissive when no `path_prefixes`; `check_url` rejects all when `hosts` is empty). Override action name is `scope_binding` (distinct from `secret_scan`, per ADR-0004's per-action token design).

## Wiring: `plugins/evidence/hooks/hooks.json`

Add a **second** `PreToolUse` entry (do not widen the secret_scan matcher):

```json
{ "matcher": "WebFetch|Edit|Write|MultiEdit",
  "hooks": [ { "type": "command",
    "command": "uv run --no-project \"${CLAUDE_PLUGIN_ROOT}/hooks/scope_bind.py\"",
    "timeout": 5 } ] }
```

## Docs

- **Extend ADR-0004** with a "scope-binding gate (shipped)" note: the `scope_binding` action is now an enforced hook, not a referenced-future one.
- **`evidence/README.md`** — describe scope-binding as a hook (not only a scaffold); document the manifest location and the override flow.
- **`SECURITY.md`** — update the scope-binding entry, which currently describes a design-level scaffold.

## Testing: `plugins/evidence/tests/test_scope_bind.py`

Drive `main()` with crafted stdin payloads (monkeypatch `sys.stdin`) and `EVIDENCE_SCOPE_PATH` pointed at a temp manifest. Follow the existing evidence test idiom (temp key + `issue_token` for the override case, mirroring the `evidence_hmac` tests).

| Case | Manifest | Tool / input | Expect |
|------|----------|--------------|--------|
| Dormant | none | any tool | exit 0 |
| URL in scope | `hosts: [example.com]` | WebFetch `https://example.com/x` | exit 0 |
| URL out of scope | `hosts: [example.com]` | WebFetch `https://evil.com` | exit 2 |
| Path in scope | `path_prefixes: [/eng/]` | Write `/eng/a.txt` | exit 0 |
| Path out of scope | `path_prefixes: [/eng/]` | Write `/etc/passwd` | exit 2 |
| Not gated | loaded | Bash / WebSearch / Read | exit 0 |
| Override | `hosts: [example.com]` | WebFetch `https://evil.com` + valid `scope_binding` token | exit 0 + notice |
| Malformed stdin | n/a | non-JSON | exit 0 |

## Done bar

`pytest` green · coverage ≥90% on `scope_bind.py` · `bash scripts/verify.sh` all-green · `feat(evidence)` version bump via `ci/release.py` · `plugins/evidence/CHANGELOG.md` + root `CHANGELOG.md` (manual) · README + SECURITY.md + ADR-0004 updated · `claude plugin validate ./plugins/evidence --strict`.

## Out of scope (future toggles, not this plan)

- Best-effort URL/path extraction from **Bash** command text.
- Blocking **WebSearch** entirely while a scope is loaded.
- Gating **Read** against `path_prefixes`.

Each is a deliberate later decision, not an oversight — recorded here so the gaps are explicit.
