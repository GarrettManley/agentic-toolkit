"""Exploit template: npm minimatch CVE-2022-3517 (GHSA-f8q6-p94x-37v3) — guard-presence probe.

Advisory facts (confirmed against osv.dev/GHSA at task-3 implementation time):
  CVE: CVE-2022-3517
  GHSA: GHSA-f8q6-p94x-37v3
  Package: npm minimatch
  Affected: < 3.0.5
  Fixed: 3.0.5
  Root cause: catastrophic backtracking in braceExpand(); fixed in 3.0.5
  (commit a8763f4) by factoring the length check into assertValidPattern(pattern)
  and calling it from braceExpand() (plus the main entry and the Minimatch ctor).
  3.0.4 already had a 1024*64 (65536) length guard, but ONLY inside parse() — its
  braceExpand() is unguarded. Verified against the 3.0.4-vs-3.0.5 minimatch.js
  source diff, 2026-06-26.

Design decisions:
  - SENTINEL_CONFIRMED is the single source of truth for the success output.
  - expected_trigger_sha256 is derived from SENTINEL_CONFIRMED offline with hashlib —
    computed once here, never recomputed at runtime.
  - Only two constant sentinels ever reach trigger.js stdout; the TypeError message
    goes to stderr. This keeps expected_trigger_sha256 stable across runs and machines.
  - Mechanism: call minimatch.braceExpand() with a >64KB pattern (70000 chars).
    minimatch 3.0.5's braceExpand calls assertValidPattern → throws → PATCHED →
    refuted. minimatch 3.0.4's braceExpand is unguarded → returns silently →
    VULN_CONFIRMED → verified. (Probing minimatch(path, pattern) does NOT split the
    versions: both hit parse()'s pre-existing 64KB guard and throw.)
  - This is the deterministic v1 signal: confirms the resolved version lacks the 3.0.5
    DoS-mitigation guard. True ReDoS detonation (timing-based) is deferred; this
    guard-presence probe is sufficient to split affected/fixed reliably.
  - Empirical validation: minimatch@3.0.4 → VULN_CONFIRMED (no-throw), minimatch@3.0.5
    → PATCHED (throws 'pattern is too long'); confirmed via docker run on 2026-06-26.
"""
from __future__ import annotations

import hashlib

from verify.strategy import PocPlan, SeedIncomplete

# ---------------------------------------------------------------------------
# Constants — single source of truth for sentinel strings and the hash
# ---------------------------------------------------------------------------

#: Emitted to stdout (+ newline) when the version lacks the 3.0.5 length guard
#: → affected/unpatched → verdict verified.
SENTINEL_CONFIRMED: str = "VULN_CONFIRMED"

#: Emitted to stdout (+ newline) when the length guard is present (patched).
SENTINEL_PATCHED: str = "PATCHED"

# Computed offline from SENTINEL_CONFIRMED + "\n" — never recomputed at runtime.
# trigger.js writes the SAME constant to stdout on minimatch@3.0.4.
_EXPECTED_SHA256: str = hashlib.sha256(
    (SENTINEL_CONFIRMED + "\n").encode()
).hexdigest()

# ---------------------------------------------------------------------------
# trigger.js template
# ---------------------------------------------------------------------------

_TRIGGER_JS_TEMPLATE: str = """\
// trigger.js — minimatch CVE-2022-3517 guard-presence probe
// Probes braceExpand() directly with a >64KB pattern. The 3.0.5 fix added a call
// to assertValidPattern() inside braceExpand() (throws TypeError('pattern is too
// long') for patterns over MAX_PATTERN_LENGTH = 1024*64). 3.0.4's braceExpand has
// NO such guard — its only 64KB check lives in parse(), which braceExpand runs
// before, so braceExpand() returns silently on 3.0.4 but throws on 3.0.5.
// (Probing minimatch(path, pattern) instead would NOT split the versions: both
// reach parse()'s pre-existing 64KB guard and throw — verified against the 3.0.4
// vs 3.0.5 source diff, 2026-06-26.)
//
// minimatch 3.0.4 — braceExpand unguarded → returns silently → VULN_CONFIRMED (exit 0)
// minimatch 3.0.5 — braceExpand guarded   → throws           → PATCHED (exit 1)
//
// Only the two constant sentinels reach stdout; the exception message goes to stderr.

"use strict";
const minimatch = require("minimatch");
const OVERLONG = "a".repeat(70000); // > MAX_PATTERN_LENGTH (65536)
let threw = false;
try {{
  minimatch.braceExpand(OVERLONG);
}} catch (e) {{
  threw = true;
  process.stderr.write("length guard present (patched): " + e.message + "\\n");
}}
if (!threw) {{
  process.stdout.write("{sentinel_confirmed}\\n");  // no length guard -> affected/unpatched -> verified
  process.exit(0);
}} else {{
  process.stdout.write("{sentinel_patched}\\n");    // guard present -> fixed -> refuted
  process.exit(1);
}}
"""

# ---------------------------------------------------------------------------
# Public factory — registered in TEMPLATE_REGISTRY by templated.py
# ---------------------------------------------------------------------------

def build(hypothesis: dict) -> PocPlan:
    """Build a PocPlan for CVE-2022-3517 (minimatch guard-presence probe).

    Reads the resolved version from hypothesis["target"]["version_or_revision"].
    Raises SeedIncomplete if the version is missing or blank.

    The installed version determines the verdict at harness runtime:
      - minimatch@3.0.4 → no length guard → VULN_CONFIRMED → VERDICT_VERIFIED
      - minimatch@3.0.5 → length guard present → PATCHED → VERDICT_REFUTED

    Args:
        hypothesis: A hypothesis dict as produced by Stage 4b.

    Returns:
        A PocPlan ready for the install→trigger sandbox phases.

    Raises:
        SeedIncomplete: if target.version_or_revision is missing or blank.
    """
    version: str | None = hypothesis.get("target", {}).get("version_or_revision")
    if not version or not version.strip():
        raise SeedIncomplete(["target.version_or_revision"])

    trigger_js = _TRIGGER_JS_TEMPLATE.format(
        sentinel_confirmed=SENTINEL_CONFIRMED,
        sentinel_patched=SENTINEL_PATCHED,
    )

    return PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "--no-save", f"minimatch@{version}"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256=_EXPECTED_SHA256,
        files={
            "trigger.js": trigger_js,
            "package.json": '{\n  "name": "poc",\n  "version": "1.0.0",\n  "private": true\n}\n',
        },
        template_id="npm:minimatch:CVE-2022-3517",
    )
