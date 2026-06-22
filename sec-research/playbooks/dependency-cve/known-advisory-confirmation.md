# Dependency CVE — Known Advisory Confirmation

**Trace ID**: trace-pb-2026-06-22-001
**Last updated**: 2026-06-22 (seed playbook; Stage 4b cold-start)

## When to look for this
Recon (`known_advisories`) already surfaced an OSV/GHSA advisory for an in-scope
package, and the package's `resolved_version` falls inside the advisory's
`affected_range` and is not at/above `fixed`. The hypothesis is that the resolved
version is genuinely affected and the vulnerable code path is reachable.

## Signal patterns (positive indicators)
- `known_advisories` is non-empty for the asset.
- `resolved_version` is within an advisory `affected_range` (and below `fixed`).
- The advisory has a concrete `cve` id and a named `package`.
- The asset `ecosystem` is one of npm / pypi / cargo / rubygems.

## False-positive patterns (negative indicators)
- `affected_range` is open-ended/overly broad with no fixed version (huntr rejects these).
- The advisory is already patched in `resolved_version` (resolved >= `fixed`).
- The advisory targets a different package than the asset (transitive-only; v1 targets the direct asset).
- No `vulnerable_function_path` is plausibly reachable from the asset's usage.

## Evidence template
A `dependency-cve` finding (see `schema/evidence.schema.json`) must produce:
`package_ecosystem`, `package_name`, `affected_versions_range`,
`vulnerable_function_path` (filled by Stage 4c), `cve_id_proposed_or_assigned`,
`attack_vector` (20+ chars). Stage 4b seeds all but `vulnerable_function_path`.

## Dedup heuristics
A confirmed known-CVE on a current version is frequently a duplicate. Before
drafting, check `deduplication_check` against nvd / ghsa / osv. If the advisory
is already public with a CVE and a fix exists, this is informational unless the
finding demonstrates a still-unpatched reachable path the advisory missed.

## Citations
- [1] The OSV/GHSA advisory record itself (Tier 1).
- [2] The package registry metadata confirming `resolved_version` (Tier 1).
