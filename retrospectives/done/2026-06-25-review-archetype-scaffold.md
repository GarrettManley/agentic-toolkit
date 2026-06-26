# Retrospective: Review New-Archetype Scaffolding (#12)

**Plan:** `~/.claude/plans/2026-06-25-review-archetype-scaffold.md`
**Commit:** `4c13b9b` (`feat(review): new-archetype scaffolding for /review-evolve (#12) (#18)`)
**Date:** 2026-06-26

## Outcome

Shipped `review@1.3.0`, closing the new-archetype scaffolding D3 deferred. `review_cli.py scaffold <name>` writes a structurally-valid `agents/<name>.agent.md` skeleton (real frontmatter + every required section with `<placeholders>` the human fills), validated by `persona.validate_persona` before writing, dry-run by default, refusing to clobber an existing persona. `/review-evolve`'s coverage-gap note now points at it. 27 tests, 100% coverage on `review_cli.py`; PR #18 merged. Notably, **#12 was the first plugin release under D6's tag-after-merge flow** — and it proved D6 end-to-end (see below). With #12 closed, the marketplace has **0 open issues**: every advertised capability is built and working, and the release process that ships it is self-healing.

## What worked

- **D6 proven by the very next release.** `release.py --apply` bumped `review` to 1.3.0 with **no branch tag**; after the squash-merge, `release.py --tag` on `main` created and pushed `review-v1.3.0` at the squash commit — the first release in the whole program needing **zero** manual `git tag -f` reconciliation. Shipping the fix (D6) and exercising it one PR later is the tightest validation loop possible: the tooling change wasn't just unit-tested, it was confirmed in production.
- **Embedded skeleton + a validity-pin test.** Building the persona from an embedded `_PERSONA_SKELETON` string (rather than transforming the human-facing `persona-stub.md`) made the output self-contained and guaranteed-valid; `test_skeleton_is_valid` pins it so it can't silently drift below `validate_persona`'s bar. This is the standing pattern from D3/D5: separate the deterministic core from the human-judgment layer.
- **Reuse over reinvention.** `scaffold` is ~30 lines because it leans entirely on D3's `persona.validate_persona` + `persona.atomic_write` and the established dry-run/`--apply`/project-local-default conventions. The whole feature was one focused subcommand.
- **The in-context file tracking.** `review_cli.py`/`persona.py` were "unchanged since last Read," so the harness served them from context — no re-read needed to edit precisely against D3's structure.

## Friction / bugs

- **My own D3 issue cited the wrong stub path**
  - *What happened:* The #12 issue (and the D3 retro's follow-up note) referenced `plugins/review/templates/persona-stub.md`; the file actually lives at `plugins/review/skills/reviewer-personas/templates/persona-stub.md`.
  - *Root cause:* The D3 exploration agent reported a `templates/persona-stub.md` path loosely; I filed the follow-up issue from that without re-verifying the path.
  - *How caught:* A `Read` of the cited path returned "File does not exist" at the start of #12 planning.
  - *Fix:* Located the real path; the plan/command/README all reference the correct one. (No code depended on the path — the embedded-skeleton decision sidestepped reading the stub entirely.)
  - *Rule:* A path written into a *filed issue* is a future instruction to yourself — verify it against the tree before filing, the same as a path in a plan. Stale paths in deferred-work issues rot exactly like stale paths in specs.

- **Relative path resolved against the wrong repo (recurring, low-cost)**
  - *What happened:* The first `Read` used a `plugins/review/...` relative path, which resolved against the Workspace cwd, not the marketplace dev clone → not found.
  - *Root cause:* The session cwd is the Workspace; the marketplace is a nested clone, so relative paths need the full `C:\Users\Garre\source\repos\claude-marketplace\...` prefix.
  - *How caught:* "File does not exist. Note: your current working directory is C:\Users\Garre\Workspace."
  - *Rule:* In this workspace, always address the marketplace dev clone by absolute path; Glob with a `path:` arg into it is also unreliable (seen in D3) — prefer absolute `Read`/`Bash ls`.

## Concrete improvements

- **New-archetype scaffolding ships** — the `evolve`/`scaffold` split (refine existing vs. create new) is the complete Post-Cycle Update Protocol now; `/review-evolve`'s deferred gap-note is resolved. Done.
- **D6 retired the tag toil for real** — #12's clean `--tag` run is the evidence. The five-waves-of-manual-reconciliation problem is gone, and the next release will confirm it again for free. Done (proven).
- **Program complete, 0 open issues** — the original goal ("everything proposed or TODO, full and working") is met. No follow-ups filed from #12.
- **Process note (carried from D5's retro, now actionable):** the D5 retro flagged that "retros only pay off if read before the next similar plan." #12 lived that out in miniature — the wrong stub path was a D3 artifact I'd have caught by re-reading the D3 follow-up note critically. The habit worth keeping: before planning a follow-up, re-verify every concrete reference in the issue that filed it.
