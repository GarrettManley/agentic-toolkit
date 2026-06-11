# Retrospective: Standing Agent/Workflow Orchestration Defaults

**Plan:** `~/.claude/plans/i-m-quite-a-fan-iridescent-hollerith.md`
**Commit:** `4b970d9` (`docs(hb-28u.8): standing agent/workflow orchestration defaults`) — home repo
**Date:** 2026-06-10

## Outcome

The harness now carries a standing orchestration policy: `~/.claude/context/agent-orchestration.md` (always-injected via `inject_context.py` auto-discovery — zero settings changes), a restated authorization section in `~/CLAUDE.md` (defense-in-depth: direct instruction outranks hook-injected context), bead hb-28u.8 filed for the phase-2 plugin migration, a `type: project` auto-memory citing it, and the uncommitted design spec under `docs/superpowers/specs/`. Category-based Workflow pre-authorization, delegate-by-default with a >~3-file floor, and the haiku/sonnet/inherit model-routing table all live.

## What worked

- **Pre-execution adversarial review (3 parallel critics: mechanism / policy design / ops-drift)** — fixes were folded into the plan before any file was written; execution was then purely mechanical.
- **Riding the existing injection surface** — `inject_context.py`'s `glob("*.md")` auto-discovery meant the new context file went live with no settings or hook changes; this session is itself the proof (the policy block is present in injected context).
- **Dual-layer placement** — CLAUDE.md restates the authorization sentence directly, so the policy survives even if context injection ever degrades.
- **The retrospective-as-feedback-loop design held** — the plan explicitly deferred judgment on the policy to real usage, and the same day delivered two full arcs (clean-state, doc-currency #162) under it.

## Same-day field test (the plan's open questions, answered)

- **Category list right-sized?** Yes — the doc arc's 9-agent per-family audit fan-out ran under the standing code-review/audit authorization with no per-task ask, exactly as intended. No category felt missing or over-broad.
- **Delegation floor (>~3 files) hold up?** Yes — single-file lookups stayed inline; family-scale audits delegated. No friction observed.
- **Model routing quality misses?** One, and it sharpened the rule: a haiku-routed "mechanical" sweep inverted the spaced em-dash title convention and invented a frontmatter exemption. Root cause: a convention *lookup* is judgment work wearing mechanical clothes. The routing rule-of-thumb ("route down only when the task is mechanical AND the output is cheaply verifiable") already covers this — the miss was in classifying the task, not in the policy. Captured in `project_aether_quality_pass` memory and the doc-arc retro.
- **local-orchestrator precedence friction?** None — the Ollama tier wasn't needed for any interactive search this session.

**Gate verdict:** policy proven in practice; proceed with hb-28u.8 (plugin migration) when picked up. The context file remains the cheap live-editable layer until then — decommission it in the same change that lands the plugin version (never both live).

## Friction / bugs

- **Down-routed agent doing judgment work**
  - *What happened:* haiku sweep agent confidently reported an inverted convention during the doc arc.
  - *Root cause:* "mechanical sweep" task framing hid an embedded judgment call (convention lookup).
  - *How caught:* reading doc-conventions §3 directly before acting on the agent's claim — prevented a wrong-direction 23-file rewrite.
  - *Fix:* verify convention sources inline before any mass edit driven by a down-routed agent.
  - *Rule:* the haiku row of the routing table is for tasks whose output is cheaply verifiable; treat any agent claim that *gates* an edit as needing source verification.
- **Retro marker went stale across compactions** — this retrospective was written a session-segment late; the pending marker was the only thing that surfaced it. The marker + SessionStart nag mechanism worked as designed — keep trusting it.

## Concrete improvements

- **hb-28u.8** — phase-2 migration into `orchestration@garrettmanley` (skill + inject hook + local-orchestrator trigger reconciliation + static `model` frontmatter on marketplace agents). Filed, ready queue (follow-up).
- **Routing-table calibration evidence** — one real-world haiku miss documented here and in auto-memory; feed it into the plugin migration's skill text (follow-up, part of hb-28u.8).
- **Context file registered** in `~/.claude/context/README.md` (done).
