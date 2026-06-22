# Retrospective: `aether login` device-code OAuth CLI (slice C3)

**Plan:** `~/.claude/plans/superpowers-writing-plans-let-s-create-elegant-matsumoto.md`
**Tracker:** follows up #139, #168; spawned + shipped #222, #223
**Date:** 2026-06-22 (residual close-out via session-recovery pass — tracker hb-bam)
**Outcome:** DONE — both #222 (CLI) and #223 (security follow-up) shipped to master
(`ade5542`, `3b4b32c`), ff-only, branches deleted. TDD RED→GREEN; real TLS via
`https.request` (zero new deps). Three independent review passes caught real bugs (readline
EOF hang, loopback-regex bypass → consolidated to `isLoopbackServer()` in aether-protocol).

## Notes
- `rl.close()` emits `close` synchronously — resolve the line *before* closing.
- Loopback detection must parse the hostname, never a regex prefix — that was the security
  follow-up, shipped together with the feature rather than deferred.
