# Retrospective: Land the aether per-edit hook debounce (hb-2ni)

**Plan:** `~/.claude/plans/writing-plans-let-s-write-a-iterative-minsky.md`
**Commit:** `e0f1e59` (`chore(dev-loop): defer per-edit tsc to a Stop hook (hb-2ni)`) — PR #231, merged to aether `master` 2026-06-27
**Date:** 2026-06-28 (reconstructed from the plan, `bd show hb-2ni`, and PR #231; the work landed in a prior session, so this records the outcome rather than re-running verification)

## Outcome

Cut aether's per-edit latency tax. The old dev loop ran `tsc --noEmit + eslint + docs:graphs:ts`
on **every** `.ts` Edit/Write via `.claude/settings.local.json`; the fix replaces that with a
two-hook debounce — a PostToolUse marker-drop (`mark_ts_dirty.mjs`) plus a Stop-time deferred
typecheck (`deferred_typecheck.mjs`) that runs `tsc` **once per edit-burst** and surfaces type
errors via `{decision:"block"}`. eslint and graph regen were deliberately dropped from the edit
loop (eslint stays on the authoritative pre-push gate; graphs become on-demand). Shipped as three
new committed `.claude/` files + a `.gitignore` re-include flip + a `ci-and-guards.md` doc update,
on branch `chore/defer-ts-typecheck-hook` → PR #231 (merged). `hb-2ni` is CLOSED.

## What worked

- **"Verify-and-land, not build" framing.** The code was already written and manually verified
  in the working tree (2026-06-25); naming the task as evidence-gather + gate-pass (not
  implementation) kept it from drifting back into a redesign and made the scope a few commands.
- **Direct hook exercise with the real stdin payload shape** (`echo '{"tool_input":{"file_path":"src/foo.ts"}}' | node …`)
  proved all four behaviors — `.ts`→marker, `.py`→none, clean→silent exit 0, type-error→single
  `{decision:block}` + marker cleared — without needing a live Claude turn.
- **Marker-clear-first idempotency.** `deferred_typecheck.mjs` deletes `.ts-dirty` *before*
  running `tsc`, so an edit-burst is nudged at most once even if the hook crashes or times out.
- **Branch + PR discipline.** Off-`master` branch, exact-file staging, full pre-push gate (no
  `--no-verify`), `bd close` on merge — the change shipped clean through gitleaks + `npm run check`
  (incl. cargo test + vitest coverage vs WSL2 Postgres) + vale 0 errors.

## Friction / bugs

No bugs recorded — the landing passed the full gate on the merge attempt. The friction was
structural / environmental, anticipated by the plan's risk list and realized as expected:

- **Heavy pre-push for a trivial `.claude/` change.**
  - *What happened:* Landing a tooling-only diff still ran the entire aether suite (cargo test +
    vitest coverage + DB integration + vale), requiring `node_modules`, the Rust toolchain, and
    an awake WSL2 Postgres.
  - *Root cause:* aether's pre-push gate is whole-suite, not path-scoped.
  - *How caught:* Anticipated in the plan ("budget minutes, not seconds"); not a surprise.
  - *Rule:* For tooling-only changes in a whole-suite-gated repo, stand up the full env
    (node_modules, Rust, **WSL2 Postgres awake, force `127.0.0.1`**) *before* pushing, so a
    failure is a real signal, not infra.

## Concrete improvements

- **Deferred-typecheck hooks shipped** — `.claude/hooks/{mark_ts_dirty,deferred_typecheck}.mjs`
  + `.claude/settings.json`, wired PostToolUse (5s) + Stop (90s). Status: done, on aether `master`.
- **Scope-narrowing documented** — `docs/engineering/ci-and-guards.md` records the Stop-deferred
  model and that per-edit eslint/graphs were intentionally moved off the edit loop. Status: done.
- **Phase 3 — live activation** (one-time hook-trust approval next time Claude starts inside
  `aether-engine` + a live smoke: instant PostToolUse on `.ts` edit, exactly one `tsc` at Stop,
  block-once on an introduced error). Status: **follow-up**, deferred to the next aether session.
- **Open watch-item** — confirm in real use that losing *per-edit* eslint doesn't bite (it's only
  covered pre-push now). The narrowing held in review; live confirmation rides with Phase 3.
