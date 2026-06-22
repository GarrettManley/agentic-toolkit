# Retrospective: Aether TUI/TTS stabilization arc

**Plan:** `~/.claude/plans/writing-plans-let-s-create-a-rippling-summit.md`
**Tracker:** #204 (done); #210, #207, #206, #209, #208 (Phase 2–3, tracked open)
**Date:** 2026-06-22 (residual close-out via session-recovery pass — tracker hb-bam)
**Outcome:** PARTIAL→tracked — Phase 1 landed #204 (Stage-3 character voices):
`test_tts_voices.ts` audible-verified offline, dead `ATTRIBUTED_DIALOGUE_RULE` removed,
missing fs/os/path imports fixed, `npm run check` green, committed to its PR. Phase 2
root-caused the #210 TUI corruption (`SoundPlayer.PlaySync` blocks the Node event loop);
the non-blocking refactor + robustness hardening (Phases 2–3) remain open under their issues.

## Notes
- `SoundPlayer.PlaySync()` blocking the event loop starves Ink's render → overlap + input
  drift. The fix must play non-blocking while preserving FIFO span ordering.
- Marker cleared (plan retro captured here); the unfinished phases live on their GitHub
  issues, not on this plan.
