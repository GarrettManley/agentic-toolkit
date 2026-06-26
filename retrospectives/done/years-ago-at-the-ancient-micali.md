# Retrospective: Modernize & Complete ScrumEstimator

**Plan:** `~/.claude/plans/years-ago-at-the-ancient-micali.md`
**Commit:** `43ed464` (`style: apply prettier formatting`) — tip of `modernize-v2`, 9 commits, PR #31
**Date:** 2026-06-25

## Outcome

Revived `GarrettManley/ScrumEstimator` — an abandoned 2020 Angular 9 UI shell with no working
backend — as a complete, modern planning-poker app and opened PR #31. Delivered M0–M5 as a
ground-up Angular 22 (standalone, signals, zoneless) rebuild on the Firebase modular SDK:
anonymous-auth rooms, hidden voting enforced in Firestore rules, live presence, client-side
bring-your-own-key Claude estimation, round history, CSV export, spectator mode, timer,
distribution chart, custom decks, plus CI/CD, accessibility, and a dev/prod config split. All
gates green: ESLint, 34 Vitest unit, 16 Firestore rules tests, 4 Playwright e2e (2 axe a11y).

## What worked

- **Two rounds of `/adversarial-review-plan` before any code** — caught the load-bearing design
  flaws while they were still cheap: OpenAI browser-CORS is unreliable (killed multi-provider),
  the OAuth "save your key" rationale was void (key is localStorage; dropped OAuth), the
  hidden-vote `get()`-per-vote rule hits Firestore's 20/query limit (→ facilitator aggregates at
  reveal), and the Java/emulator prereq. The plan got materially simpler and safer each round.
- **Milestone-per-commit with a full gate each time** (lint + unit + rules + e2e) — every
  regression surfaced at the boundary it was introduced, never compounded.
- **TDD on pure logic** (deck classification, consensus, AI parsing, CSV) — emulator-independent,
  so real progress continued while the JDK install was pending.
- **Emulator + `@firebase/rules-unit-testing` for the security crux** — 16 rules tests proved
  hidden-vote enforcement before any UI existed.
- **Playwright two-context e2e** — the only honest proof of the realtime loop; doubles as the
  scripted multi-client demo the review asked for.
- **Nested repo under `apps/` via the allow-list `.gitignore`** — the modernized app keeps its
  own remote/history with zero parent-repo pollution; verified with `git check-ignore`.

## Friction / bugs

- **JDK version floor**
  - *What happened:* installed OpenJDK 17; firebase-tools rejected it ("no longer supports Java
    before 21").
  - *Root cause:* assumed any LTS JDK; didn't check firebase-tools' minimum.
  - *How caught:* `emulators:exec` error.
  - *Fix:* installed OpenJDK 21.
  - *Rule:* firebase-tools 15.x needs JDK 21+; verify a tool's runtime floor before installing.

- **winget PATH not visible to the running session**
  - *What happened:* after install, `java` was still "command not found" in the Bash tool.
  - *Root cause:* the Bash tool's shell inherits the session PATH captured at launch; a machine
    PATH update from winget doesn't reach it.
  - *Fix:* prepend the JDK `bin` per command.
  - *Rule:* on Windows, winget/MSI PATH changes need a new session or an explicit prepend.

- **@angular/fire lags the Angular major**
  - *What happened:* latest `@angular/fire` (20) doesn't support Angular 22.
  - *How caught:* `npm view @angular/fire peerDependencies` during M0.
  - *Fix:* used the raw Firebase modular SDK + hand-written `toSignal` wrappers (the plan's named
    contingency).
  - *Rule:* check `@angular/fire`'s peer range against the target Angular major before depending on it.

- **`Round.aiSuggestion` dropped in a model rewrite**
  - *What happened:* M2 build failed — the template referenced `aiSuggestion`, absent from `Round`.
  - *Root cause:* the M1 full-file rewrite of `models.ts` silently lost a field present in the
    original.
  - *How caught:* `ng build` template type-check.
  - *Fix:* re-added the field.
  - *Rule:* when overwriting a type/model file, diff against the prior shape rather than retyping
    from memory.

- **WCAG AA contrast failures**
  - *What happened:* axe flagged color-contrast on the gray/teal palette over the light background.
  - *Root cause:* the ported 2020 palette assumed dark backgrounds; bright teal + mid-gray fail AA
    for small text on light.
  - *How caught:* the axe-core e2e pass (added in M5).
  - *Fix:* darkened the secondary text color and introduced a dark-teal for text/links/ghost
    buttons (kept bright teal for backgrounds/accents).
  - *Rule:* add an axe gate early; brand colors rarely pass AA for small text — reserve them for
    fills, not text.

- **`snapToDeck` tie expectation wrong**
  - *What happened:* expected `snapToDeck('4', fib)` → `5`; it returns `3`.
  - *Root cause:* `reduce` without an explicit tie-break keeps the first-seen best (3 before 5).
  - *How caught:* writing the test and tracing it honestly.
  - *Fix:* corrected the assertion + documented the tie behavior.
  - *Rule:* trace `reduce` tie-breaking; don't assume "nearest" resolves ties upward.

## Concrete improvements

- **Facilitator-aggregates-at-reveal** — votes write-only/own during voting; facilitator computes
  `round.results` once at reveal. Sidesteps the `get()`-per-vote 20/query limit. (`firestore.rules`
  + `RoomStore.reveal`, done.)
- **Round-keyed "has voted" (`votedRoundId`)** — avoids a cross-user `hasVoted` reset on each new
  round (rules only allow self-writes). (`RoomStore`, done.)
- **Dev/prod env split** — emulator + demo project in dev, real config via `environment.prod.ts`
  fileReplacement in prod. (`src/environments/*`, done.)
- **CI with rules + e2e + opt-in deploy** (rules/indexes before hosting). (`.github/workflows/ci.yml`,
  done.)
- **Follow-ups (pending, operator/user):** merge PR #31 + default-branch swap; fill real Firebase
  config + enable Anonymous auth + CI deploy secrets; one-shot real-key AI smoke test (logic is
  unit-tested with a mocked fetch).
