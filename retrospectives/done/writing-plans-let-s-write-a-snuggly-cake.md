# Retrospective: spec-047 World-Fact Closure (#235 + #236)

**Plan:** `~/.claude/plans/writing-plans-let-s-write-a-snuggly-cake.md`
**Commit:** `66224c0` (`docs(world-map): satisfy Vale prose rule (for example, not e.g.) (#235)`) — range `3660f98..66224c0`, 9 commits
**Date:** 2026-06-28

## Outcome

Closed the two deferred follow-ups on the spec-047 world-fact layer (default-on in the Aether Engine, `Workspace/Roleplaying`). **#235:** a pure, deterministic `filterWorldFacts` pass (`src/world-map/worldfact-filter.ts`) that *normalizes* genitive place-anchoring to recover the proper place ("Amber Spire's fallen" → "Amber Spire") and *drops* common-possessor junk + past-tense historical-remnant clauses — wired into the production apply path (`event-router.ts routeStageDirections`, with OVERSEER rejection audit) and the extraction eval, guarded by a golden-derived precision regression test (0.667 → 1.000 on the labeled corpus). **#236:** token-`usage` capture (`drainUsage()`) on `LlamaCppProvider`, summed per turn into the gameplay harness `TurnRecord.contextTokens` (was hardcoded `null`). Merged ff-only to master, full `npm run check` green (1306 tests, coverage above all floors, contract 26/26), pushed. **Live GPU validation (N-run precision average for #235, non-null contextTokens for #236) and GitHub issue closure remain** — they are documented in the plan's Verification section and gated on an idle llama-server.

## What worked

- **`/adversarial-review-plan` before coding** — the single highest-value step. Three independent agents (skeptic / feasibility / scope-cutter) caught three *design* defects that would have shipped: (1) the original drop-every-possessive design would have destroyed real golden-set positives ("Amber Spire's fallen defenders" etc.) → redesigned to normalize-not-drop; (2) the present-action guard shared tokens (`mark`/`names`) with historical-remnant phrasing, neutering the filter on its own canonical example; (3) the frozen-corpus precision gate was circular → demoted to a behavioral guard with the ≥0.80 claim moved to the live N-run eval. Fixing these on paper cost minutes; in code they'd have been silent recall loss in production.
- **Subagent-driven execution with per-task spec+quality review** — 7 tasks, fresh subagent each, two-stage review caught the harness scope bug and kept blast radius tight (final whole-branch review found zero new Critical/Important).
- **`/adversarial-review-code` after implementation** — byte-level inspection caught the curly-apostrophe regex bug that every test (written with ASCII apostrophes) passed over.
- **Providing fully-verified fixtures in task briefs** — the precision corpus was pre-traced through the filter, so the deterministic gate passed first try with the exact predicted numbers.

## Friction / bugs

- **Harness `llm` out of scope (runtime ReferenceError, gate-invisible)**
  - *What happened:* the #236 harness edit referenced `llm.drainUsage()` in `main()` scope, but `llm` was `const` inside the `wireFreshState` closure.
  - *Root cause:* `tsconfig.json` `include` is `src*,gen*,packages*` — **`scripts/` is not typechecked**, so `npm run check` reports clean while the harness has a hard scope error (it only runs via ts-node).
  - *How caught:* IDE language-server diagnostics (which check all files) flagged `Cannot find name 'llm'`; `npm run typecheck` did not.
  - *Fix:* hoisted `llm` to outer `main()` scope (`let llm!: LlamaCppProvider;`), mirroring the existing `dm` pattern (`b177379`).
  - *Rule:* `scripts/` is outside the type gate — treat IDE diagnostics as authoritative there, and consider adding a `scripts/` typecheck pass (deferred follow-up).

- **Curly-apostrophe regex class collapsed to two ASCII apostrophes**
  - *What happened:* `GENITIVE_ANCHOR`'s class intended `[ASCII-apostrophe, U+2019]` but both bytes were `0x27`, so possessives written with a typographic apostrophe (common in LLM prose) bypassed the filter entirely.
  - *Root cause:* a literal `'`/`'` glyph pair in the plan code was transcribed as two identical ASCII apostrophes — invisible in a normal diff.
  - *How caught:* `/adversarial-review-code` did a byte-level (`hexdump`) inspection of the character class.
  - *Fix:* rewrote the class with an explicit `’` escape + added a curly-apostrophe regression test (`57b0541`).
  - *Rule:* when a regex/string literal must contain a non-ASCII character, write it as a `\uXXXX` escape in the plan and the source — never a bare glyph, which silently mis-transcribes.

- **Stale IDE diagnostics fired mid-edit (3×)**
  - *What happened:* `<new-diagnostics>` reported "module not found" / "property does not exist" right after each subagent finished, contradicting the agent's green test run.
  - *Root cause:* diagnostics were captured from an intermediate edit state and lagged the final on-disk file.
  - *How caught:* re-running the actual test / grepping the on-disk file every time.
  - *Rule:* treat post-edit diagnostics as a prompt to verify on disk, not as ground truth — but never dismiss them without checking (the harness scope bug was a *real* diagnostic among the stale ones).

- **Doc gate trailers (`e.g.`, `last-verified` format)**
  - *What happened:* the pre-push Vale gate rejected `e.g.` (Google.Latin rule); separately, my task brief wrongly told the implementer to set `last-verified` to a date when the convention is a commit SHA.
  - *How caught:* Vale at pre-push; the SHA-vs-date issue by a per-task reviewer + a convention grep.
  - *Fix:* `for example` (`66224c0`); `last-verified: 02bebd3` (`b5bb3f1`).
  - *Rule:* doc edits answer to Vale/markdownlint/frontmatter gates — brief doc tasks with the actual convention (SHA for `last-verified`, "for example" not "e.g.").

## Concrete improvements

- **`scripts/` typecheck gap** — `scripts/` is excluded from `tsconfig.json`; harness type errors escape `npm run check`. Follow-up: add a `scripts/`-scoped typecheck (or include it). Status: **pending follow-up** (not filed).
- **Live validation + issue closure** — run the N-run live eval (#235 precision ≥0.80, recall ~0.85) and `AB_INSTRUMENT=1` harness run (#236 non-null `contextTokens`) on an idle llama-server; fold real emissions into `tests/fixtures/worldfacts/observed-corpus.json`; then close #235/#236 with the measured numbers. Status: **pending (GPU-gated)**.
- **Deferred adversarial-review findings** (non-blocking) — eval `catch {}` masks infra errors as empty emission; `parsed.worldFacts` cast trusts unvalidated LLM JSON (pre-existing, `llamacpp.ts`); `normalizeGenitivePlace` recovers a titled person ("Lord Halveth's keep" → "Lord Halveth") and emits no OVERSEER normalize-audit; `drainUsage` lives only on the concrete provider (intentional #236 scope). Status: **deferred**, recorded here for triage.
- **Plan-authoring rule** — encode non-ASCII regex literals as `\uXXXX`. Status: **applied** in this branch; worth carrying into the writing-plans habit.
