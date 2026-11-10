# Retrospective: SOLID + Clean Architecture standard, wave 1 of 4 (hb-w4h)

**Plan:** `~/.claude/plans/i-m-looking-to-apply-curious-acorn.md` (epic); wave plan
`docs/superpowers/plans/2026-10-29-hb-w4h-1-standard-bindings-persona.md`
**Commit:** `f60bc4f` (`docs(plans): record wave-1 verification evidence and completion (hb-w4h.1)`), Workspace
`master`; marketplace PR #63, squash `313e8ea`
**Date:** 2026-11-10
**Scope:** wave 1 only. Waves 2-4 (gm-common library, consumer swaps, template and gates) stay open as
hb-w4h.2, hb-w4h.3 and hb-w4h.4. A retrospective for the whole epic follows wave 4.

## Outcome

The Workspace now has one written design standard, `docs/standards/solid-clean-architecture.md`, covering the
dependency rule, earned abstraction, SOLID with the workspace's own exemplars, the reuse rule and a reviewer
checklist. It is bound as the `/deliver` constitution in six repos: Workspace root, sec-research, System.Control,
mtga-companion, Roleplaying and claude-marketplace. Two Workspace gates the wave tripped were repaired first: the
`WORKSPACE_SKIP_PUBLISH` valve and the `pre_commit_audit.ps1` prune list (hb-64f). The marketplace gained the
`review:architecture-conformance` code-diff persona. `docs:adversarial-review-code` now dispatches it on source
diffs with a `--constitution` argument, which `deliver` forwards. That shipped as review 1.4.0, docs 1.2.0 and
delivery 0.4.0, tagged at `313e8ea`. Every Verification line passed on 2026-10-29; evidence is in the wave plan's
sibling `.evidence.md`. The plan had 41 adversarial-review findings, all resolved or deferred before execution.
There were two task-review fix rounds: Task 0's `.venv` escape and Task 4's rubric decidability.

## What worked

- **Adversarial plan review before execution.** The 41 findings included both gate trips (the post-commit site
  publish and the audit descending into nested clones). Task 0 repaired them before any wave commit, so no commit
  needed `[verify-override]`.
- **Generic persona, mirrored checklist.** The public persona embeds a project-free checklist that is word for word
  the standard's reviewer section. A grep for project and identity names in the persona file prints nothing, so
  publishing the marketplace leaks nothing private.
- **Seeded-diff proxy for persona behaviour.** A pre-release dispatch on a seeded diff checked the important case:
  a `blocker` for an outward import, and no demand for a port on in-process code with one implementation (the
  plan's anti-goal). The persona's behaviour was checked before any release existed.
- **Release tooling by the book.** Bumps ran on the branch before the squash, `release.py --tag` ran after it on
  main (ADR-0012), and all seven CI checks passed on the first run.

## Friction / bugs

- **Wave complete, landing stalled for 12 days**
  - *What happened:* every task and verification line finished on 2026-10-29, but the Workspace branch stayed
    unmerged and unpushed, and the marketplace PR was never opened. Landing waited on authorization and the
    session moved on to other work. The persona was not live in that time, and later unrelated commits
    (retrospectives) piled onto the wave's feature branch.
  - *Root cause:* the Landing section handed off to "on explicit authorization" with nothing tracking that
    pending authorization. hb-w4h.1 stayed open with no landing reminder, so it read as in progress.
  - *How caught:* a cross-repo consolidation on 2026-11-10 found the branch and the open marketplace branch.
  - *Fix:* landed during that consolidation: Workspace fast-forward, PR #63 merged, release tagged.
  - *Rule:* when a plan's last step needs authorization, ask for it in the same session the verification passes.
    If it can't be given then, file a landing bead with the exact commands so the work never looks finished
    while unlanded.
- **Completion check passed an unfinished epic**
  - *What happened:* `plan_completion_check.py` reported the epic plan COMPLETE while three of four waves were
    open.
  - *Root cause:* the epic plan lists its waves as prose, not checkboxes, and its Retrospective placeholder text
    ("To be written after the last wave") counts as a non-placeholder section.
  - *How caught:* reading the plan before writing this retrospective.
  - *Rule:* epic plans list their waves as `- [ ]` items, so the completion check sees open waves.
- **Private-project retrospectives queued for a public push**
  - *What happened:* the Workspace remote is public. Retrospectives about a private repo had accumulated in its
    unpushed history, including on this wave's branch.
  - *Fix:* they were moved into that private repo and stripped from the unpushed Workspace commits before the
    first push; that repo's CLAUDE.md now records where its retrospectives go.
  - *Rule:* before pushing the Workspace repo, check its unpushed retrospectives for private-repo content.

## Concrete improvements

- **Landing-in-session rule.** In this retrospective and the session memory; pending adoption in plan templates.
- **Epic plans use wave checkboxes.** Done for the hb-w4h epic plan (wave 1 ticked, waves 2-4 open).
- **First live `docs:adversarial-review-code` dispatch of the persona.** Pending. It needs the plugin cache
  reinstalled at the new versions; record the dispatch under the wave plan's Verification acceptance 2.
- **Waves 2-4.** hb-w4h.2, hb-w4h.3 and hb-w4h.4, open.
