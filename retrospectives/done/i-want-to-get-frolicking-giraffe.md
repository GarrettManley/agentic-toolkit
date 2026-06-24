# Retrospective: claude-marketplace Production-Grade v1.0 Public Launch

**Plan:** `~/.claude/plans/i-want-to-get-frolicking-giraffe.md`
**Commit:** `d07cfae` (`docs(W3+W4): full README estate + engineering docs + GitHub meta for v1.0`)
**Date:** 2026-06-24

## Outcome

Took the private `GarrettManley/claude-marketplace` from mid-flight to publish-ready across
every workstream except the terminal, operator-gated recreation (W8). On `scrub/v1-prep` @
`d07cfae`: publish-safety scrub + context relocation (W0, `92d07f3`), `origin/main` agent
expansion merged and normalized to a single `*.agent.md` convention (Wm `fd49371` / Wn
`4790bc9`), cross-platform + init/setup subsystem (W1/W2, `c6151db`), test coverage to 99%
with the all-20 agent-contract suite (W5, `043b264`+`38e171c`), tri-OS CI matrix + linters +
LICENSE/NOTICE attribution gate (W7, `3f15da1`/`2d39b3c`/`158a537`), full README + engineering
doc estate (W3/W4, `d07cfae`), and the 1.0.0 version reset with standardized CHANGELOGs (W6,
`0b96951`). Only **W8** (clean repo recreation + tag/release + manual visibility flip) remains,
deliberately deferred as destructive and operator-gated (tracked `hb-28u.9.9`).

## What worked

- **Per-workstream bead decomposition (hb-28u.9.1–.11)** — each W-stream mapped to its own bead
  with the commit SHA recorded in the plan header, so resume-after-crash was unambiguous about
  what had landed vs. what was pending.
- **Hybrid execution model** — subagent-driven fan-out for the doc/test workstreams (W3/W4/W5,
  fresh agent per plugin) + inline checkpointed execution for the mechanical git/manifest
  surgery (Wm/Wn/W6). Matching execution style to task shape avoided both over- and
  under-orchestration.
- **Hardened blocklist grep as the publish-safety gate** — a single case-insensitive,
  slash-agnostic pattern (user path, corporate repo names, hardware specifics, bead ids) gave a
  mechanical, repeatable check that the public tree is scrubbed.
- **Releases-stay-local decision (C1)** — keeping `ci/release.py` local and CI verify-only
  sidestepped an entire class of accidental-publish risk; the scopeless squash subject keeps
  `release.py` a no-op at HEAD.

## Friction / bugs

- **In-flight test failures surfaced only at merge**
  - *What happened:* W5 carried 6 failing tests through the `043b264` WIP checkpoint, fixed in
    `38e171c` after the `origin/main` merge.
  - *Root cause:* coverage tests were checkpointed pre-merge to preserve work across a risky
    merge, so they co-existed with the incoming agent expansion before being reconciled.
  - *How caught:* the W5.0 "verify the in-flight tests" resume step in the plan handoff.
  - *Fix:* fixed the 6 failures and added the all-20 agent-contract suite once the merged agent
    set was final.
  - *Rule:* when checkpointing WIP tests ahead of a merge, make "re-run + reconcile the
    checkpointed tests" an explicit first post-merge step — a green checkpoint is not a green
    merge.

- **Agent filename convention drift from the merge**
  - *What happened:* the merged `origin/main` brought agents in a mix of naming styles needing a
    normalization pass (Wn, `4790bc9`) before they could be tested/documented uniformly.
  - *Root cause:* two branches evolved the agent estate independently (decision D2 — single
    `*.agent.md` convention — postdated the divergence).
  - *How caught:* planned Wn normalization step gated W5.4/W3.
  - *Fix:* renamed all 20 agents to `*.agent.md`; regenerated skill-index.
  - *Rule:* land a naming/convention decision before fanning out parallel work that produces
    files in that namespace, or budget an explicit normalize step downstream of the merge.

## Concrete improvements

- **W8 verification gate (plan §W8.5)** — comprehensive terminal checklist (matrix green,
  coverage ≥90%, blocklist=0, NOTICE present, identity == personal email, no `refs/pull/*`,
  recreated-repo CI green). Status: **pending** — operator-gated, tracked `hb-28u.9.9`.
- **Manual post-actions checklist (plan §Manual)** — evidence-key regen, `tiers.local.json`
  confirm, marketplace re-add, visibility flip. Status: follow-up for Garrett post-W8.
- **Open questions for the W8 retro addendum** — did recreation purge all GitHub-side residue;
  did the ≥90% Python gate hold across the matrix; did `release.py` survive the squash; did
  NOTICE satisfy license scanners; did consumers self-heal; was init one-command on all 3 OSes.
