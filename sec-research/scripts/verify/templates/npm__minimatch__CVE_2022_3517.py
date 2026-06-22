"""Exploit template: npm minimatch CVE-2022-3517 (GHSA-f8q6-p94x-37v3) — guard-presence probe.

Advisory facts (confirmed against osv.dev/GHSA at task-3 implementation time):
  CVE: CVE-2022-3517
  GHSA: GHSA-f8q6-p94x-37v3
  Package: npm minimatch
  Affected: < 3.0.5
  Fixed: 3.0.5
  Root cause: catastrophic backtracking in braceExpand(); fixed by introducing
  MAX_PATTERN_LENGTH = 1024*64 (65536) and assertValidPattern(pattern) in 3.0.5
  (commit a8763f4), which throws TypeError('pattern is too long') for patterns
  exceeding the length cap.

Design decisions:
  - SENTINEL_CONFIRMED is the single source of truth for the success output.
  - expected_trigger_sha256 is derived from SENTINEL_CONFIRMED offline with hashlib —
    computed once here, never recomputed at runtime.
  - Only two constant sentinels ever reach trigger.js stdout; the TypeError message
    goes to stderr. This keeps expected_trigger_sha256 stable across runs and machines.
  - Mechanism: feed a >64KB pattern (70000 chars). minimatch 3.0.5 throws via
    assertValidPattern (length guard) → PATCHED → refuted. minimatch 3.0.4 has no
    length guard → reaches braceExpand/match silently → VULN_CONFIRMED → verified.
  - This is the deterministic v1 signal: confirms the resolved version lacks the 3.0.5
    DoS-mitigation guard. True ReDoS detonation (timing-based) is deferred; this
    guard-presence probe is sufficient to split affected/fixed reliably.
  - Empirical validation (3.0.4 → VULN_CONFIRMED, 3.0.5 → PATCHED) pending a
    docker-capable run.
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
// Feeds a >64KB pattern to minimatch.  The 3.0.5 fix introduced
// MAX_PATTERN_LENGTH = 1024*64 (65536) and assertValidPattern(pattern) that
// throws TypeError('pattern is too long') for patterns exceeding the cap.
//
// minimatch 3.0.4 — no length guard → reaches match silently → VULN_CONFIRMED (exit 0)
// minimatch 3.0.5 — length guard present → throws → PATCHED (exit 1)
//
// Only the two constant sentinels reach stdout; the exception message goes to stderr.

"use strict";
const minimatch = require("minimatch");
const OVERLONG = "a".repeat(70000); // > MAX_PATTERN_LENGTH (65536) introduced by the 3.0.5 fix
let threw = false;
try {{
  minimatch("probe-target", OVERLONG);
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
