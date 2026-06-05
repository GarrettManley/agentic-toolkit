# Stage 2 Venue Surface — Read-Only Research

**Date**: 2026-05-07
**Purpose**: Inform brainstorming for Stage 2 (Program Intake). Stage 1 complete; Stage 2 builds venue scope fetchers that emit `programs/<slug>/scope.yaml` validated against `schema/program.schema.json`.

---

## 1. Existing Repo References Per Venue

### huntr.com
- `hooks/pretooluse.py:29` — `api.huntr.com`, `huntr.com` in PT-2 `SUBMISSION_VENUE_HOSTS`
- `schema/program.schema.json:16` `venue` enum has `huntr`; `:79` `submission.protocol` has `huntr-api`
- `scripts/setup_credentials.py:27-30` — service `huntr-api`, help URL `huntr.com/settings/api`
- `scripts/submit.py:30`, `scripts/sign_approval.py:31` — in `VENUE_CHOICES` but stubbed (Stage 7)
- `docs/SCOPE_SCHEMA.md:7-49` — canonical example uses huntr (`loaded_from: huntr.com/repos/<owner>/<pkg>`)
- `docs/PLAYBOOK_FORMAT.md:51-52` — anti-slop note: "huntr rejects findings where `affected_versions_range` is overly broad"
- `tests/fixtures/huntr-test-program/scope.yaml` — concrete fixture with `venue: huntr`, `manual-form` submission
- `CLAUDE.md` preamble — huntr is the v1 anchor venue

### GHSA
- `hooks/pretooluse.py:30` — `api.github.com` ("gh api for ghsa")
- `schema/program.schema.json:16,79` — `ghsa` venue, `ghsa-cli` protocol
- `schema/finding.schema.json:194` — `ghsa` is a dedup source
- `scripts/submit.py:174-254` — `_dispatch_ghsa()` is **fully implemented** in Stage 1: `gh api --method POST /repos/{o}/{r}/security-advisories`
- `docs/CREDENTIAL_HANDLING.md:30,37` — no keyring entry; `gh auth login` token reused
- `docs/SUBMISSION_GATE.md:65-69` — GHSA is Stage-1-FULL
- `README.md:25` — example: `load_program.py --venue ghsa --identifier <repo-slug>`

### IBB on HackerOne
- `hooks/pretooluse.py:31` — `api.hackerone.com`, `hackerone.com` in PT-2 set
- `schema/program.schema.json:16,79` — `ibb-h1`, `h1` venues; `h1-api` protocol
- `scripts/setup_credentials.py:31-38` — both `h1` and `ibb-h1` use `hackerone-api` service
- `scripts/submit.py:30` — in `VENUE_CHOICES`; `_dispatch_stub()` (Stage 7)
- **No fixture, no notes, no docs detail beyond enum membership.** IBB's surface is the thinnest in the repo.

---

## 2. Per-Venue Analysis

### 2A. huntr.com

- **API**: No documented public API for scope listing. Programs are URL-addressable via `huntr.com/repos/<owner>/<pkg>`. **Fetcher will likely HTML-scrape or use unofficial JSON.** Document captured-version explicitly.
- **Auth (intake)**: None — public pages. Submission-side `huntr-api` token deferred to Stage 7.
- **Required scope fields**: `program_slug = huntr-<owner>-<pkg>`; `venue = huntr`; `venue_program_id = <owner>/<pkg>`; `loaded_from` = canonical program URL; `in_scope[]` ≥ 1 `package` (with `ecosystem`) + 1 `repo` (`github.com/<owner>/<pkg>`); `submission.protocol = manual-form` (Stage 1) or `huntr-api` (Stage 7).
- **Gotchas**:
  - huntr requires AI-disclosure → `rules.ai_disclosure_required: true`
  - Ecosystem inference: huntr URL doesn't always reveal ecosystem; either probe linked repo manifest (cross-cuts Stage 3) or leave `ecosystem: null` for human edit
  - Stage-5 dedup needs `programs/<slug>/disclosed/`; `load_program.py:80` already creates the empty dir
  - Default rate limit: 60/min per `SCOPE_SCHEMA.md:38`

### 2B. GHSA

- **API**: `gh api /repos/{o}/{r}` and `/repos/{o}/{r}/security-advisories`. **Each repo = one program** — no central GHSA program directory.
- **Auth**: existing `gh auth login`. Zero keyring entries.
- **Required scope fields**: `program_slug = ghsa-<owner>-<repo>`; `venue = ghsa`; `submission.protocol = ghsa-cli`; `venue_program_id = <owner>/<repo>`; `loaded_from = github.com/<owner>/<repo>/security/advisories`; `in_scope[]` ≥ 1 `repo`; add `package` only if discoverable from repo's manifest.
- **Gotchas**:
  - No `max_payout_usd` for GHSA repos — omit (schema-optional)
  - "Is repo accepting advisories?" — public probe via `/repos/{o}/{r}/security-advisories` (cheap, idempotent)
  - Conservative `ai_disclosure_required: true` default unless maintainer's CONTRIBUTING.md says otherwise
  - Schema quirk: protocol is `ghsa-cli`, not `gh-api`

### 2C. IBB on HackerOne

- **API**: H1 REST + GraphQL at `api.hackerone.com`. IBB is a single H1 program (`hackerone.com/ibb`) covering many OSS packages with a structured asset list. Fetcher must enumerate the asset list.
- **Auth**: H1 API token (basic auth `username:api_token`); service `hackerone-api` already wired. **IBB read may require researcher-tier reputation — verify before committing.**
- **Required scope fields per asset**: `program_slug = ibb-<asset>`; `venue = ibb-h1`; `submission.protocol = h1-api` (Stage 7) or `manual-form` (Stage 1 stop-gap); `venue_program_id` = H1 asset id; `in_scope[]` from `eligible_submissions` payload; `rules.embargo_period_days` from program metadata; populate `ai_assistance_allowed` / `ai_disclosure_required` from H1's per-program AI policy field.
- **Gotchas**:
  - IBB has firm 90/120-day embargoes — fetch and respect
  - Don't confuse VDP-only assets with bounty-eligible assets; check `bounty_eligible: true`
  - Default `rate_limit_per_min: 60` is conservative against H1's higher actual ceiling
  - **One big `programs/ibb-h1/scope.yaml` vs one per-asset `programs/ibb-<asset>/`?** Recommend per-asset (matches per-package model elsewhere; cleaner `program_slug` semantics)
  - Token denial fallback: scaffold-style YAML for manual completion (matches `load_program.py:71` scaffold pattern)

---

## 3. Decomposition Recommendation

**Order**: huntr → GHSA → IBB.
1. **huntr first** — v1 anchor venue (CLAUDE.md), exercises most schema fields (payouts, AI-disclosure, venue-specific submission), and existing `tests/fixtures/huntr-test-program/` is a ready golden test.
2. **GHSA second** — repo=program is conceptually simplest; submission half already done; building second confirms abstraction generalizes.
3. **IBB last** — auth gating + multi-program traversal + possibly multiple programs per fetch is highest friction.

**Smallest end-to-end-testable slice (sub-stage 2.1)**:
- `scripts/fetch_program.py --venue huntr --identifier <owner>/<pkg>`
- Tests use `--from-fixture <path>` flag — no live HTTP; fixture under `tests/fixtures/huntr-fetch/`
- Emits valid `programs/<slug>/scope.yaml` after `validate_program()` passes
- Test pattern from `tests/hooks/test_pt1_scope.py`: load fixture → fetcher emits scope → assert schema-valid → PT-1 then accepts an in-scope target
- Unit tests: slug derivation, ecosystem fallback, `loaded_from` provenance, protocol defaulting, idempotency on re-fetch

**Deferred**: 2.2 GHSA fetcher (~<100 LOC since `gh api` does the work); 2.3 IBB-H1 fetcher; later — scope freshness checks (`loaded_at` >90d), scope-diff alerts on re-fetch, scope drift detection.

---

## 4. Fetcher Contract Sketch

**Single CLI, multi-venue dispatch** (mirrors existing `submit.py --venue`):

```python
# scripts/fetch_program.py
def fetch_program(
    venue: str,                       # "huntr" | "ghsa" | "ibb-h1"
    identifier: str,                  # huntr/ghsa: "owner/pkg"; ibb-h1: "asset-id"
    *,
    from_fixture: Path | None = None, # bypass live HTTP for tests
    force: bool = False,              # overwrite existing scope.yaml
) -> tuple[bool, str, dict]:
    """Returns (ok, slug, scope_dict). On ok: writes programs/<slug>/scope.yaml +
    scaffolds disclosed/, notes.md, targets.txt (matches load_program.py layout)."""
```

**Integration with `load_program.py`**: Refactor `load_program.py`'s write path into a shared `_write_scope(slug, data)` helper both scripts call. Reuses `validate_program` (`hooks/lib/schema_validate.py`) and `invalidate_scope_cache` (`hooks/lib/scope_match.py`). Single validation path, no duplication.

**Error handling**:
- Network failure → `(False, "", {})`, exit 1, no partial file written
- Schema-invalid emit → write to `scope.draft.yaml` (NOT `scope.yaml`, so PT-1 doesn't pick up an invalid scope), exit 1
- Existing scope without `--force` → exit 1 (matches `load_program.py:78`)

**Idempotency**:
- `safe_dump(..., sort_keys=False)` already preserves order
- `loaded_at` is the only timestamp — exclude from idempotency hash
- Optional sibling `provenance.json`: raw upstream payload + ETag/SHA for diff-detection on re-fetch (Stage 2.3+)

**Network-call invariant — bootstrap problem**:
The fetcher's HTTP calls happen BEFORE the program is loaded, so PT-1 will block them. Three options:
- (a) Hardcode `BOOTSTRAP_FETCHER_HOSTS` in `pretooluse.py` (huntr.com, api.github.com, api.hackerone.com — already in `SUBMISSION_VENUE_HOSTS`)
- (b) Require signed override per fetch (annoying)
- (c) Tool-name match exempts `fetch_program.py` from PT-1
**This is a Stage-1 hook contract amendment — flag explicitly for the spec.**

---

## 5. Open Questions for Garrett

1. **CLI shape**: Unified `fetch_program.py --venue X` vs three per-venue scripts? (Recommend unified — mirrors `submit.py`.)
2. **PT-1 bootstrap**: How does the fetcher itself reach huntr.com / api.github.com / api.hackerone.com BEFORE a program is loaded? Hardcoded bootstrap host list, signed override per fetch, or tool-name exemption? Picking this slightly amends Stage 1's hook contract.
3. **Ecosystem inference for huntr**: When huntr's page doesn't expose ecosystem, do we (a) probe the linked repo's manifest, (b) leave `ecosystem: null` for human edit, or (c) call a Stage-3 helper (couples Stage 2→3)?
4. **IBB granularity**: One `programs/ibb-h1/scope.yaml` with many `in_scope[]`, or one program-dir per IBB asset? (Recommend per-asset.)
5. **Re-fetch policy**: When `loaded_at` is >90d, auto-trigger from `nightly.py`, warn at PT-1 hook time, or require manual `--force`?
6. **huntr API access tier**: HTML-scrape public pages now, or wait until Stage 7 huntr token is provisioned and unify intake+submit auth? (Recommend HTML-scrape now, document in `notes:`.)
7. **Provenance file**: Emit `programs/<slug>/provenance.json` (raw upstream + content hash) for drift detection? Would need a tiny schema addition.
8. **IBB token-denial fallback**: Hard-fail, emit scaffold for manual completion, or fall back to public-page scrape?
9. **AI-policy mapping**: Auto-populate `rules.ai_assistance_allowed` / `ai_disclosure_required` from upstream venue policy fields, or always default to most-conservative? (Recommend: populate from upstream; default conservative only if upstream silent.)
10. **Disclosed-findings backfill**: Stage 2 fetcher creates the empty `programs/<slug>/disclosed/` only — backfilling actual disclosed reports is a Stage 5 concern. Confirm boundary.
