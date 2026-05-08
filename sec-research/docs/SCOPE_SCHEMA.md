# Scope Schema (`programs/<slug>/scope.yaml`)

Each loaded program has a normalized scope file that is the single source of truth for what targets are in/out of scope. PT-1 hook validates every network call against this. UPS-2 hook validates every prompt-mentioned identifier against this.

Format conforms to `schema/program.schema.json`.

## Canonical example (huntr.com program)

```yaml
program_slug: huntr-org-acme
venue: huntr
venue_program_id: acme-org
loaded_at: 2026-05-07T14:00:00Z
loaded_from: https://huntr.com/repos/acme-org/acme-pkg
display_name: "Acme Org — acme-pkg"

in_scope:
  - asset_type: package
    identifier: acme-pkg
    ecosystem: npm
    tier: high
    max_payout_usd: 500
    notes: "Active maintained package, weekly downloads ~50k"

  - asset_type: repo
    identifier: github.com/acme-org/acme-pkg
    notes: "Source repo for the package"

out_of_scope:
  - asset_type: host
    identifier: blog.acme.org
    reason: "Marketing site; not part of the bounty"

rules:
  ai_assistance_allowed: true
  ai_disclosure_required: true
  rate_limit_per_min: 60
  user_agent_required: "Garrett-Manley-SecResearch/1.0 (huntr.com/research)"
  no_dast_against_prod: false
  embargo_period_days: 90
  notes: "Maintainer prefers responsible disclosure timeline; coordinates via GitHub Security Advisories."

submission:
  protocol: huntr-api
  endpoint: https://api.huntr.com/v1/reports
  auth_ref:
    service: huntr-api
    username: garrettmanley
```

## Required top-level fields

| Field | Purpose |
|-------|---------|
| `program_slug` | kebab-case unique slug; matches the `programs/<slug>/` directory name |
| `venue` | enum: huntr / ghsa / ibb-h1 / h1 / bugcrowd / intigriti / direct-maintainer |
| `loaded_at` | ISO 8601 timestamp; programs older than 90d should be re-fetched |
| `loaded_from` | URL provenance — where this scope was sourced from |
| `in_scope[]` | List of in-scope asset entries |
| `out_of_scope[]` | List of explicit out-of-scope asset entries |
| `rules` | Program rules including AI-assistance posture |
| `submission` | Protocol + endpoint + credential reference |

## `in_scope[]` / `out_of_scope[]` entry fields

| Field | Required | Purpose |
|-------|----------|---------|
| `asset_type` | yes | enum: package / repo / url / host / ip-range / binary |
| `identifier` | yes | Canonical identifier per asset_type |
| `ecosystem` | for package | npm / pypi / cargo / maven / gem / nuget / etc. |
| `tier` | optional | critical / high / medium / low |
| `max_payout_usd` | optional | Used by `sign_approval.py` to display expected payout range |
| `notes` | optional | Human notes |
| `reason` | for out_of_scope | Why this is excluded |

## `rules` fields

| Field | Type | Purpose |
|-------|------|---------|
| `ai_assistance_allowed` | bool | If false, UPS-2 hook hard-blocks any agentic engagement with this program |
| `ai_disclosure_required` | bool | If true, finding.md must include an AI-assistance disclosure section |
| `rate_limit_per_min` | int | PT-1 enforces this against per-host request counts |
| `user_agent_required` | string | All HTTP requests must use this User-Agent |
| `no_dast_against_prod` | bool | If true, PT-1 blocks DAST patterns against production hostnames |
| `embargo_period_days` | int | Default disclosure timeline; informs `sign_approval.py` review prompt |

## `submission` fields

| Field | Required | Purpose |
|-------|----------|---------|
| `protocol` | yes | enum: huntr-api / ghsa-cli / h1-api / email / manual-form / bugcrowd-api / intigriti-api |
| `endpoint` | optional | URL for API protocols; mailto: for email |
| `auth_ref` | optional | `{service, username}` pair resolved via `keyring` (NEVER credentials inline) |

## How scopes get loaded

- **Stage 2** will provide automated scope fetchers that produce these YAML files
- **Stage 1** loads scopes manually via `scripts/load_program.py --venue <v> --identifier <id>` or by hand-writing the YAML

## Validation

`scripts/load_program.py` validates against `schema/program.schema.json` before writing. PT-1 hook re-validates on every load (cached).
