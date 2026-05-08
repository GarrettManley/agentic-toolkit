# Evidence Discipline

This is the single most important quality contract in the workspace. Findings without proper evidence get rejected as "AI-slop"; findings WITH proper evidence get accepted regardless of who/what generated them.

## The three evidence requirements (per finding)

Every finding must have ALL THREE before any commit to `findings/<trace>/` succeeds:

### 1. `Citation:` line(s) — Tier-1 source(s) for every claim

Every `Fact:` or `Claim:` line in finding.md must be followed by `Citation:` and `Proof:` lines. Format inherited from `citation-seeker` skill:

```markdown
**Fact**: The `acme-pkg@1.2.3` `runShell()` function passes user input directly to `child_process.exec`.

**Citation**: [1] https://github.com/acme-org/acme-pkg/blob/v1.2.3/src/shell.js#L42
**Proof**:
    function runShell(input) {
        return require('child_process').exec(input);  // line 42 — bug
    }
```

Source tiers (from `truth-seeker`):
- **Tier 1 (auto-approve)**: Official docs, GitHub READMEs, RFCs, source code at a specific commit
- **Tier 2 (corroborated)**: Peer-reviewed papers, expert blogs from recognized researchers
- **Tier 3 (community, leads only)**: SO answers, blog posts — REQUIRES a Tier-1/2 corroborator URL

Tier-3 sources without a corroborator are hard-blocked by PT-4 + verify_finding.py.

### 2. Runnable PoC at `findings/<trace>/poc/reproduce.sh`

The PoC must:
- Be a single command from the researcher's perspective: `./reproduce.sh`
- Run inside `sandbox_server.py` (Docker isolation, no network unless scope explicitly permits)
- Have a deterministic outcome OR explicit `deterministic: false` in finding frontmatter with rationale
- Declare `expected_exit_code` (0 = vuln present, non-zero = vuln absent — convention varies; document per-finding)
- Have an `expected_output_hash` (SHA-256 of stdout) for fully-deterministic PoCs

PoCs are validated by `verify_finding.py` which runs them in sandbox and compares actual to expected.

### 3. Captured execution evidence

Three artifacts per finding:

- **`findings/<trace>/timeline.md`** — append-only record of every Bash / sandbox / browser tool call during the investigation: timestamp, command, exit_code, stdout_hash. Maintained by PoT-3 hook.
- **`findings/<trace>/evidence/redacted/`** — sanitized HTTP traces, screenshots, sandbox stdouts. Tracked in git. PT-6 hook scans for accidentally-included secrets and hard-blocks.
- **`findings/<trace>/evidence/raw/`** — unredacted captures. **Gitignored**. The redacted/ versions are the source of truth for evidence in the report.

## Required fields by vulnerability class

(See `schema/evidence.schema.json` for the machine-readable spec.)

### `dependency-cve` (Stage 1 anchor class)

| Field | Required | Notes |
|-------|----------|-------|
| `package_ecosystem` | yes | npm / pypi / cargo / maven / gem / nuget |
| `package_name` | yes | Canonical name in ecosystem |
| `affected_versions_range` | yes | Per-ecosystem range syntax (`^1.0.0 <1.2.4`, etc.) |
| `fixed_version` | optional | If known/coordinated |
| `vulnerable_function_path` | yes | `src/parser.js#L42` style |
| `cve_id_proposed_or_assigned` | yes | `CVE-NNNN-NNNNN` if assigned, `CVE-PROPOSED` otherwise |
| `attack_vector` | yes | Free text describing trigger conditions |

### `supply-chain-malicious-pkg`

| Field | Required | Notes |
|-------|----------|-------|
| `package_ecosystem` | yes | |
| `package_name` | yes | |
| `malicious_version` | yes | Specific version under analysis |
| `payload_type` | yes | enum: data-exfil / cryptominer / persistence / token-stealer / wrapper / other |
| `delivery_mechanism` | yes | enum: typosquat / dependency-confusion / account-takeover / postinstall / other |
| `c2_indicator` | optional | If applicable; URL/domain — handle as Tier-1 finding (no probing) |

### Other classes (stub fields fill in during their stage)

`code-injection`, `auth-bypass`, `ssrf`, `rce`, `info-disclosure`, `dos`, `crypto-weakness`, `logic-flaw`, `other`.

## Anti-fabrication enforcement (the AI-slop killer)

Three layers catch fabricated references independently:

1. **PT-4** (PreToolUse) — at write time, every `CVE-NNNN-NNNNN`, `pkg@version`, and commit SHA is validated:
   - CVE → NVD lookup (cached 24h)
   - Package version → registry lookup (npm view / pip index versions / cargo search / etc., cached 1h)
   - Commit SHA → GitHub API or `git ls-remote` (cached indefinitely)
2. **G-1** (git pre-commit) — `verify_finding.py` re-runs all reference validations
3. **`verify_finding.py` directly** (pre-submit) — same validations as G-1

Defense in depth. A hallucinated CVE that somehow slipped past PT-4 will be caught at G-1 OR `verify_finding.py`. Tests verify all three layers catch independently.

## Anti-emoji posture

Some venues penalize emoji-laden reports. The PostToolUse pipeline includes an optional `scrub_emojis.py` step that strips emojis from `finding.md` (keeping the body clean while not affecting markdown structure). Disable per-finding via frontmatter `keep_emojis: true` if the venue is known-permissive.
