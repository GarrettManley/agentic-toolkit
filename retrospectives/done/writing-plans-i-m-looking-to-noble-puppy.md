# Retrospective: TTS Stage 2 — fine per-character dialogue voicing

**Plan:** `~/.claude/plans/writing-plans-i-m-looking-to-noble-puppy.md`
**Tracker:** follows up #201 (TTS Stage 1), unblocked by #202
**Date:** 2026-06-22 (residual close-out via session-recovery pass — tracker hb-bam)
**Outcome:** ABANDONED ON MERIT (with retained fallback) — Phases 1–4 built
(`extractDialogue` provider, wire sites, gateway threading, TUI playback), but the Phase-6
prose A/B tournament KILLED the live flip: the `@attributed` per-line instruction scored
54 Elo below `@narrated` baseline (CI [913, 1037]). The live prompt was deliberately NOT
flipped; extraction still parses quoted speech that appears naturally in `@narrated` prose.

## Notes
- The judge (sonnet-4-6) preferred `@narrated`'s flowing atmosphere over mechanical
  quoted-line output — a real quality signal, not noise. Honoring the plan's explicit
  degradation clause beat forcing a regression.
- Kokoro audible smoke test was deferred (server not up); per-block latency / hallucinated
  speakers / json_schema path all gated on that test.
