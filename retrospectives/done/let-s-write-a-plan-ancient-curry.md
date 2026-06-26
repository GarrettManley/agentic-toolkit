# Retrospective: Retrospective → Instinct Bridge (learning Phase 2d)

**Plan:** `~/.claude/plans/let-s-write-a-plan-ancient-curry.md`
**Commit:** `0ab4a67` (`feat(learning): mine retrospectives into instincts (Phase 2d)`)
**Date:** 2026-06-26

## Outcome

Shipped `/instinct-from-retro` + `scripts/retro_mine.py` to the `learning@garrettmanley`
plugin (PR #19, `hb-4t5` closed), closing the previously write-only retrospective loop. The
script deterministically parses each retro's `## Friction / bugs` Rules and emits a JSON
friction summary; Claude clusters rules recurring across ≥2 retros and authors candidates,
which `--ingest` normalizes into a new `retro-mined` source (capped at 0.80) and writes via
the existing idempotent `write_instincts`. 14 TDD tests, 97% module coverage, all 10
`verify.sh` gates green; the parser was validated against the real 23-retro corpus
(23/10/68, matching an independent extraction exactly). Seven instincts were mined from the
strongest ≥2-retro clusters, applied, then promoted to the **global** store, and
`LEARNING_SURFACE=on` was enabled — so they now inject at every SessionStart.

## What worked

- **Brainstorming AskUserQuestion gates before planning** — locking direction (cross-cutting
  capability) / loop-closure (instinct bridge) / trigger (manual-first) as explicit decisions
  meant the adversarial pass debated *execution risk*, not *intent*.
- **`/adversarial-review-plan` (9 agents) earned its keep** — caught the markup bug that would
  have made the parser match zero retros, the 23-vs-33 yield, and the ledger-vs-clustering
  conflict; and forced the Phase 0 value-probe that answered the skeptic's premise challenge.
- **Phase 0 value-probe as a go/no-go gate** — a cheap read-only extraction proved recurrence
  (≥8 patterns) and surfaced the killer datum: the corpus *self-documents* the loop's absence
  (`briefing-renderer`: "a retro finding is not a fix; it only helps if I re-read retros…").
- **Mirroring `detect.py`'s `command = judgment / script = mechanical` split** — a proven shape
  to copy kept the non-deterministic clustering out of the tested Python.
- **Reusing `write_instincts` / `instinct_schema` / `surface.py`** — no new storage; the
  surface-at-SessionStart loop closed for free, and the schema change was one line.
- **The corpus paid off during its own build** — the `Glob --path` unreliability and the
  coverage-source-path gotcha both bit exactly as two mined rules predicted.

## Friction / bugs

- **Plan asserted bold markup; retros use italic sub-labels**
  - *What happened:* the plan's parser spec keyed on `**Rule:**` (bold); real retros use italic
    `*Rule:*`. A bold-keyed parser matches zero of 23 retros.
  - *Root cause:* wrote the parser spec from a glance that conflated the entry's bold *header*
    with its italic *sub-labels*.
  - *How caught:* three adversarial-review agents cross-checked against line 27 of a real retro.
  - *Fix:* parser keys on an italic/bold-tolerant `\*+Label[...]:\*+` regex; the test fixture
    was copied verbatim from a real retro.
  - *Rule:* when writing a parser for a semi-structured doc, copy the target markup verbatim
    into a fixture before specifying the regex — never infer the format from a glance.

- **Glob with a `path:` arg into the marketplace returned nothing**
  - *What happened:* `Glob` into the nested marketplace clone returned "No files found" though
    the tree exists, seeding a false plan premise ("dev clone has no learning tree").
  - *Root cause:* `Glob`'s `path:` arg into the nested clone is unreliable — a pre-existing
    gotcha already recorded in the retro corpus (`review-archetype-scaffold`).
  - *How caught:* Bash `ls` showed the tree; a feasibility agent flagged the false premise.
  - *Fix:* addressed the clone by absolute Bash `ls`/`Read`; corrected the plan's Step 0.
  - *Rule:* enumerate the marketplace dev clone with absolute Bash `ls`/`Read`, not `Glob`'s
    `path:` arg.

- **Coverage invoked with a file path instead of the import name**
  - *What happened:* `--cov=plugins/learning/scripts/retro_mine` collected no data ("module
    never imported"); the tests import `retro_mine` (scripts/ is on `sys.path` via conftest).
  - *Root cause:* passed the filesystem path to `--cov`; coverage keys on the import name.
  - *How caught:* the coverage warning + an empty report.
  - *Fix:* `--cov=retro_mine`.
  - *Rule:* scope coverage by the import name the tests actually use (matching the conftest
    `sys.path` injection), not the file path.

- **Instincts applied to project scope, hiding them from the sessions they'd help**
  - *What happened:* `--apply` ran from the marketplace-clone cwd with `--scope project`, so the
    7 cross-project-wisdom instincts landed in that clone's project store, invisible to
    Workspace sessions.
  - *Root cause:* the plan defaulted to project scope conservatively, without reasoning that
    retro-derived workflow wisdom is inherently cross-project.
  - *How caught:* a post-apply file-location check; surfaced to the user, who chose to promote.
  - *Fix:* `/promote` each id to global (copy-verify-delete; 7 global / 0 project).
  - *Rule:* retro-mined instincts are cross-project wisdom — default them to global scope (or
    promote immediately); project scope hides them from the very sessions they'd help.

## Concrete improvements

- **Phase 0 value-probe pattern** — a cheap read-only go/no-go gate before building, answering
  "is the payoff real?" before spending effort. Generalizable to any premise-risky plan. Done
  (used here; reusable).
- **`commands/*.md` are still un-CI-linted** — the recurring mined finding bit *again* this
  plan: `verify.sh`'s `lint-frontmatter` scanned 52 files and skipped the new command. A real
  `commands/` frontmatter lint is overdue. Follow-up (candidate bead).
- **Default scope for `/instinct-from-retro`** — consider recommending or defaulting to global
  scope for cross-project rules, so the project-scope footgun above can't recur. Follow-up.
- **Loop-closure proof is still pending** — next-session verification that a surfaced
  retro-mined instinct visibly lands in context (and informs a decision) is the real test;
  `LEARNING_SURFACE=on` takes effect only at the next SessionStart. Pending.
