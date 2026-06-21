# Design: Stage 3 — Recon Module

**Trace ID**: trace-20260621-001 (Stage 3 of 7)
**Status**: APPROVED 2026-06-21
**Charter**: `docs/CHARTER.md` (§The seven-stage roadmap)
**Predecessor**: Stage 2 Program Intake — plan `docs/superpowers/plans/2026-06-20-stage2-program-intake.md` (shipped; tracker hb-kz6)

---

## 1. Introduction

### 1.1 Purpose

Stage 3 builds the **Recon Module**: given a loaded program scope, it assembles a per-asset
**known-vulnerability baseline of the attack surface** — registry metadata, the pinned
transitive dependency closure, a shallow clone of the in-scope source, and a correlated list
of already-known advisories. This baseline is the *context input* to Stage 4 (Hypothesis &
Test Harness); it is explicitly **not** a finding.

### 1.2 Scope

In scope for v1: asset types `package` and `repo`. Per in-scope asset, produce a **recon
item** (§5) and write supporting artifacts to `runtime/recon/<slug>/`. Fill the existing
`stage_recon(scopes) -> list[dict]` seam in `scripts/nightly.py` and `scripts/investigate.py`.

Out of scope (§9): registry-walk dependency resolution without a lockfile; cloning dependency
*source*; cross-package vulnerability inference (Stage 4); dedup of new candidate findings
(Stage 5); recon of `url` / `host` / `ip-range` / `binary` asset types.

### 1.3 The Stage 3 ↔ Stage 5 boundary

Both stages query NVD / OSV / GHSA, for opposite purposes:

- **Stage 3 (this spec)** — establishes *what is already known* about the in-scope dependency
  surface. Output is a **baseline**, consumed by Stage 4 hypothesis generation.
- **Stage 5 (Triage & Dedup)** — given a *new candidate finding* from Stage 4, decides whether
  it duplicates an existing advisory or a venue-disclosed report.

Stage 3 correlates advisories *to inventory the surface*; Stage 5 correlates *to reject
duplicates*. Stage 3 does no dedup of candidate findings.

---

## 2. Background

The substrate Stage 3 builds on (all present as of Stage 2):

| Asset | Path | Reused for |
|-------|------|-----------|
| Scope loader | `lib/scope_match.py` (`load_all_scopes`, `is_in_scope`, `host_in_scope`) | enumerate in-scope assets |
| Scope schema | `schema/program.schema.json` (`in_scope[]`: `asset_type`, `identifier`, `ecosystem`) | asset typing |
| HTTP scope gate | `lib/policy.py` (`check_http(url, *, bootstrap_hosts=...)`, `ScopeViolation`, `VENUE_BOOTSTRAP_HOSTS`) | egress gating |
| Registry lookups | `hooks/lib/registry_lookup.py` (npm/pypi/cargo/rubygems; 1h cache) | package metadata |
| Advisory lookups | `hooks/lib/nvd_lookup.py` (NVD JSON API v2; 24h cache) | CVE/CVSS enrich |
| Git lookups | `hooks/lib/git_lookup.py` (SHA validation; `git ls-remote`) | repo/commit verification |
| Stage 2 HTTP pattern | `scripts/fetchers/_http.py` | gate-before-egress chokepoint shape |
| Pipeline seam | `scripts/nightly.py`, `scripts/investigate.py` (`stage_recon(scopes) -> list[dict]`, currently `return []`) | integration point |
| Artifact root | `runtime/recon/<slug>/` (gitignored; PT-3 allows writes inside workspace) | recon output |

**Subprocess-scope gap (Charter §Known limitation):** Claude's PreToolUse hooks do not
intercept HTTP/`git` issued by a subprocess. Therefore every recon egress must gate itself by
calling `policy.check_http(...)` before the socket/subprocess — the same mitigation Stage 2's
sanctioned scripts use.

---

## 3. Requirements

### 3.1 Functional

- **R1** — For each in-scope `package` asset: resolve registry metadata (versions, latest,
  repository link, maintainers); resolve the repository; clone it (R4).
- **R2** — For each in-scope `repo` asset: clone it (R4); discover manifest(s); identify the
  package(s) it publishes.
- **R3** — Resolve the **transitive dependency closure** lockfile-first (§6.2): parse the
  ecosystem lockfile for the exact pinned tree; if absent, record direct dependencies only and
  set the `no_lockfile` flag.
- **R4** — Shallow-clone (`git clone --depth 1`) each **in-scope repo** into
  `runtime/recon/<slug>/source/<owner>-<repo>/`, capturing the resolved commit SHA. Dependency
  source is not cloned.
- **R5** — Correlate **known advisories** over the resolved closure: one OSV batch query
  (aggregates GHSA / PyPA / RustSec / npm / Go), NVD enrichment for CVE/CVSS detail, and fold
  in `programs/<slug>/disclosed/` (venue-disclosed reports captured in Stage 2).
- **R6** — Emit one **recon item** per asset (§5), validated, and return the list from
  `stage_recon(scopes)`; persist artifacts under `runtime/recon/<slug>/`.

### 3.2 Constraints (workspace invariants — hard)

- **C1 — Scope-bounded.** Every egress routes through `recon/_http.py` →
  `policy.check_http(url, bootstrap_hosts=RECON_INFRA_HOSTS)` before the socket/subprocess.
  `ScopeViolation` propagates uncaught to the CLI top level → exit 1 (carries its audit ledger
  entry; never swallowed).
- **C2 — Stage 1 is the contract.** No modification to `schema/*.json`, `hooks/policy.py`, or
  any existing hook. The recon allow-set is supplied via the existing `bootstrap_hosts`
  *parameter* of `check_http` — `policy.py` is not edited. The only existing files touched are
  the pipeline scripts `scripts/nightly.py` / `scripts/investigate.py`, whose
  `stage_recon(scopes) -> list[dict]` stubs are the designed seam to fill (not Stage-1
  contracts); everything else is new files.
- **C3 — No fabrication.** A missing lockfile, a truncated closure, a skipped clone, or a
  failed advisory source is recorded as an explicit flag — never silently presented as a clean
  or complete baseline.
- **C4 — Offline-testable.** All network/clone surfaces accept a fixture injection path so the
  full test suite runs with no network (Stage 2 convention).

---

## 4. Architecture

```
scripts/recon_program.py          # CLI: --slug <slug> | --all ; orchestrates recon for in-scope assets
scripts/recon/
  __init__.py
  _hosts.py        # RECON_INFRA_HOSTS frozenset (registry + advisory + clone hosts)
  _http.py         # gate chokepoint: check_http(url, bootstrap_hosts=RECON_INFRA_HOSTS) before egress
  metadata.py      # per-asset registry metadata (reuses hooks/lib/registry_lookup)
  deps.py          # lockfile detection + parse → bounded transitive closure (per ecosystem)
  clone.py         # shallow `git clone --depth 1` of in-scope repos; gated + size-capped
  advisories.py    # OSV batch over closure + NVD enrich + fold programs/<slug>/disclosed/
  recon_item.py    # assemble + validate the per-asset recon item; artifact writer
```

`recon_program.py` is the only orchestrator and the only component that walks scopes and
writes artifacts; the `recon/` modules are pure, fixture-injectable units. `stage_recon()` in
the pipeline scripts calls `recon_program`'s entry function (not the CLI) so the pipeline and
the standalone CLI share one code path.

### Data flow

`load_all_scopes()` → for each in-scope asset:

1. **package** → `metadata.py` (registry metadata) → resolve repo → `clone.py`.
   **repo** → `clone.py` → discover manifests → identify published package(s).
2. `deps.py` → detect ecosystem lockfile → parse exact pinned closure (cap §6.4); no lockfile →
   direct deps only + `no_lockfile`.
3. `advisories.py` → OSV batch over the closure → NVD enrich → fold `disclosed/`.
4. `recon_item.py` → assemble + validate → write `runtime/recon/<slug>/recon.json` +
   `source/`, `dep-graph/`, `metadata/`, `advisories/` artifacts → return recon-item list.

---

## 5. Output: the recon-item schema (Stage 4 contract)

```jsonc
{
  "slug": "huntr-acme-org-acme-pkg",
  "asset": {"asset_type": "package", "identifier": "acme", "ecosystem": "npm"},
  "resolved_version": "4.2.1",
  "repo": {
    "identifier": "github.com/acme-org/acme",
    "clone_path": "runtime/recon/<slug>/source/acme-org-acme",
    "commit_sha": "<sha>",
    "cloned": true
  },
  "direct_deps": [{"name": "lodash", "version": "4.17.21", "ecosystem": "npm"}],
  "transitive_closure": {
    "count": 312,
    "truncated": false,
    "path": "runtime/recon/<slug>/dep-graph/closure.jsonl"
  },
  "known_advisories": [
    {"id": "GHSA-xxxx", "cve": "CVE-2024-...", "source": "osv",
     "severity": "high", "affected_range": "<4.2.0", "fixed": "4.2.0", "package": "acme"}
  ],
  "flags": ["no_lockfile"],          // also: closure_truncated | clone_skipped:size | advisory_source_error:osv
  "recon_ts": "2026-06-21T00:00:00Z"
}
```

The large `transitive_closure` list and raw source live on disk under `runtime/recon/<slug>/`;
the recon item carries counts + a path, not the whole tree, so the `stage_recon()` return value
stays compact. A JSON Schema for the recon item ships with the implementation
(`schema/recon_item.schema.json` is **new**, additive — it is not a Stage-1 contract schema).

---

## 6. Detailed design

### 6.1 `_hosts.py` — `RECON_INFRA_HOSTS`

A curated frozenset of recon data-source hosts, treated as trust-establishing infrastructure
(the same category as `VENUE_BOOTSTRAP_HOSTS`) and allowed once any scope is loaded:

```
registry.npmjs.org, pypi.org, crates.io, rubygems.org,
api.github.com, raw.githubusercontent.com, github.com,
services.nvd.nist.gov, api.osv.dev
```

Lives in `scripts/recon/` (recon-owned). PT-1 never sees recon's subprocess HTTP, so the set
only needs to be visible to the recon script; it is passed to `check_http` via `bootstrap_hosts`.

### 6.2 `deps.py` — lockfile-first closure

Per ecosystem, detect and parse the lockfile for the exact pinned transitive tree:

| Ecosystem | Lockfile(s) parsed |
|-----------|--------------------|
| npm | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| pypi | `poetry.lock`, `Pipfile.lock`, `uv.lock` |
| cargo | `Cargo.lock` |
| rubygems | `Gemfile.lock` |

No lockfile present → parse the manifest for **direct** dependencies only and set the
`no_lockfile` flag. Resolution is deterministic and does no registry-walk (a missing lockfile is
flagged, not back-filled by resolving version ranges).

### 6.3 `clone.py` — gated shallow clone

`git clone --depth 1 <repo_url>` into `runtime/recon/<slug>/source/<owner>-<repo>/`, after
`check_http(<repo_url>)`. Capture the resolved commit SHA. Size cap (§6.4): if the repo exceeds
the cap or the clone fails, set `clone_skipped` and continue (metadata + advisories still
produced). Only in-scope repos are cloned.

### 6.4 Tunable bounds (starting values; iterate later)

- **Closure node cap:** 2000. Exceeding it truncates and sets `closure_truncated` with the
  dropped count logged.
- **Clone size cap:** 500 MB. Exceeding it (or clone failure) sets `clone_skipped`.

### 6.5 `advisories.py` — OSV-batch correlation

One OSV batch query (`api.osv.dev`) over the resolved closure is the correlation engine — OSV
aggregates GHSA, PyPA, RustSec, npm, and Go advisories, so a single batched call covers the
whole tree. NVD (`services.nvd.nist.gov`, reusing `nvd_lookup.py`) enriches matched CVEs with
CVSS/detail. `programs/<slug>/disclosed/` records (captured in Stage 2) are folded in as
venue-known items. A source erroring sets an `advisory_source_error:<src>` flag for that asset
rather than failing the run (C3).

### 6.6 Pipeline wiring

`stage_recon(scopes)` calls the `recon_program` entry function with the already-loaded scopes
dict and returns the recon-item list. `nightly.py` runs all scopes; `investigate.py` runs the
single bounded scope it was invoked for. No behavior change to the surrounding pipeline.

---

## 7. Error handling & resilience

- **Per-asset isolation** — one asset's failure (bad manifest, clone error, advisory gap) is
  captured in that item's `flags` and does not sink the program's recon run.
- **Egress denial** — `ScopeViolation` propagates uncaught → CLI exit 1 (C1).
- **Honest gaps** (C3) — `no_lockfile`, `closure_truncated`, `clone_skipped:*`,
  `advisory_source_error:*` are first-class flags on the recon item; downstream stages can see
  exactly where the baseline is incomplete.

---

## 8. Testing strategy

Offline, TDD, mirroring Stage 2's fixture discipline:

- Fixture lockfiles per ecosystem → closure parse correctness; node-cap truncation.
- Lockfile-absent → direct-deps-only + `no_lockfile`.
- Canned OSV batch + NVD JSON → advisory→recon-item mapping; `advisory_source_error` on a
  simulated source failure.
- Fixture/mocked clone → SHA capture, `clone_skipped` on cap breach.
- `check_http` gating asserted to fire **before** every egress, including `git clone`;
  `ScopeViolation` propagation to CLI exit 1.
- Recon-item schema validity for every produced item.

No live network in the suite. A documented **optional live smoke** (user-run, one in-scope
program) confirms real registry/OSV/clone behavior, per the Stage 2 precedent.

---

## 9. Out of scope (YAGNI)

Registry-walk transitive resolution without a lockfile; cloning dependency source; cross-package
vulnerability correlation/inference (Stage 4 hypothesis); dedup of new candidate findings
(Stage 5); recon of `url` / `host` / `ip-range` / `binary` assets. These can be layered on
later without reshaping the recon-item contract.

---

## 10. References

- `docs/CHARTER.md` — workspace charter, invariants, seven-stage roadmap.
- `docs/HOOK_CONTRACTS.md` — PT-1 / PT-3 / subprocess-gap details.
- `docs/superpowers/plans/2026-06-20-stage2-program-intake.md` — Stage 2 (predecessor; the
  fetcher/`_http` pattern this stage mirrors).
- `schema/program.schema.json` — scope `in_scope[]` asset shape (Stage 3 input).
- OSV API (batch query), NVD JSON API v2.0 — advisory data sources.

---

## 11. History

| Date | Change |
|------|--------|
| 2026-06-21 | Initial design. Decisions locked in brainstorm: full recon (transitive closure + advisory correlation across the tree); standing `RECON_INFRA_HOSTS` infra allow-list passed via `check_http(bootstrap_hosts=...)` (no Stage-1 edit); lockfile-first bounded closure (cap 2000 / 500 MB); OSV-batch correlation engine + NVD enrich; v1 handles `package`/`repo` only. |
