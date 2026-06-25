# Retrospective: Take the Hardware-Upgrade Dashboard Live

**Plan:** `~/.claude/plans/create-a-plan-for-starry-pixel.md`
**Commit:** `ca765b6` (`feat(hw-dashboard): Take dashboard live on real data + nightly tracking`)
**Date:** 2026-06-25

## Outcome

Operationalized the `apps/hw-dashboard` upgrade dashboard from a demo-data prototype into a
live, self-updating tool for this machine. Identified the host as an iBUYPOWER Trace Mesh
TMI7N4601 and filled the profile with verified PSU (600W 80+ Gold) and case clearance (405mm).
Ran the agent-team workflow on real web data to produce a validated 28-option recommendation
(headline: RTX 5070 Ti + 750W PSU bundle to relieve the 8GB VRAM ceiling; 97/471 claims demoted
by adversarial verification). Wired real Newegg price tracking for two decision SKUs, registered
the nightly collector with Task Scheduler (03:15 MT, test-fired green), and verified the SPA
renders the real recommendation across all four views with zero axe violations. 14 files,
+1247/−65.

## What worked

- **Zero-agent diagnostic workflow** — isolating "how does `args` arrive?" in a 5ms no-op
  workflow proved the harness stringifies `args`, instead of re-running the real 3.6M-token
  workflow to guess. Cheap experiments to localize a bug beat expensive end-to-end retries.
- **Smoke-before-full gate** — a `quick`/`gpu` run (~11 agents) caught the compat-semantics bug
  before the expensive `standard` run, so the 153-agent pass produced usable output first try.
- **Schema-as-contract validation** — validating the real `recommendation.json` immediately
  surfaced 59 conformance errors that collapsed to 3 real schema-too-strict patterns.
- **Adversarial verification visibly bit** — 97 of 471 claims demoted (votes/claim=2) is
  evidence the gate is doing work, not rubber-stamping.
- **Playwright + axe-core over MCP** — drove both the a11y audit and the real-data render check
  without local ChromeDriver (which had a version mismatch).

## Friction / bugs

- **Workflow `args` arrives as a JSON string, not an object**
  - *What happened:* First two runs returned empty with `profile` undefined; the second
    accidentally ran the full 3.6M-token sweep against an undefined profile.
  - *Root cause:* The script assumed `args.profile`; the harness delivers `args` as a JSON
    string, so every property read was `undefined` and defaults kicked in.
  - *How caught:* Zero-agent diagnostic returning `typeof args === "string"`.
  - *Fix:* `const A = typeof args === 'string' ? JSON.parse(args) : (args || {})`.
  - *Rule:* In this Workflow harness, treat `args` as possibly-stringified; parse defensively.

- **Compat-checker mapped "needs a bigger PSU" to `incompatible`**
  - *What happened:* All discovered GPUs were dropped; recommendation came back empty.
  - *Root cause:* The `fit` filter kept only `compatible`; "fits but needs a PSU upgrade" is
    semantically `conditional`, but the agent classified it `incompatible`.
  - *How caught:* Smoke test — 3 GPUs, all verdict `incompatible` with PSU-wattage reasons.
  - *Fix:* compat prompt now defines conditional vs incompatible explicitly; filter keeps both.
  - *Rule:* "Workable with one supporting upgrade" is `conditional`, not `incompatible` —
    don't silently drop the exact bundles the user asked to see flagged.

- **Schema didn't model the honest "no price yet" case**
  - *What happened:* Real output failed schema validation (null `price.citation`, extra
    `price.note`, richer `verification_summary`, bundle `supporting_upgrades`).
  - *Root cause:* The contract assumed every option has a price citation; the cold-start design
    explicitly allows untracked prices.
  - *Fix:* nullable price citation, optional `note`, extra summary counts, `supporting_upgrades`.
  - *Rule:* Model the missing-data case in the schema from the start, not after the first real run.

- **SPA white-screened on real data (`.toFixed()` on null)**
  - *What happened:* Every view rendered blank; React unmounted with no error boundary.
  - *Root cause:* `price.current_usd` / `value_per_dollar` / bundle totals are null in real data,
    but the code called `.toFixed()` unguarded — and `api.ts` typed them non-null, so `tsc` and
    the demo-data a11y audit both passed.
  - *How caught:* Playwright console on real data (`Cannot read properties of null`).
  - *Fix:* `web/src/format.ts` (`usd`/`ratio` render `—` for null), applied to 7 call sites.
  - *Rule:* Verify on real (null-bearing) data, not demo fixtures; type nullable API fields as
    nullable so the compiler catches the gap.

- **Retailer URL redirected to a gouged marketplace listing**
  - *What happened:* The RAM URL parsed to $1214.99 for a 64GB DDR5 kit (~6× real).
  - *Root cause:* The page redirected to a different (DDR5-6600) SKU with a third-party seller
    price; the parser trusts the first Product block.
  - *How caught:* Price-sanity eyeball on the parse output before creating the SKU file.
  - *Fix:* Deferred RAM tracking; tracked only the price-sane, offer-URL-matching GPU + PSU.
  - *Rule:* Validate a parsed retailer price (sanity range + offer-url matches fetched url)
    before trusting it; don't poison the series with phantom prices.

## Concrete improvements

- **`web/src/format.ts` null-safe formatters** — `apps/hw-dashboard/web/src/`, done.
- **Workflow args parse + conditional filter + compat/scout prompts** — `workflows/upgrade-dashboard.workflow.js`, done.
- **Schema relaxations for honest missing-data** — `schema/recommendation.schema.json`, done.
- **a11y: contrast token + h1** — `web/src/styles.css`, `App.tsx`, done (0 axe violations).
- **Nightly collector registered + test-fired** — Task Scheduler `hw-dashboard-nightly`, done.
- **RAM price tracking** — needs a clean first-party URL — follow-up (noted on hb-62n).
- **Parser price-sanity / offer-url guard** — harden `collector/retailers/jsonld.py` against
  redirects + gouged listings — follow-up (noted on hb-62n).
- **`api.ts` nullable typing** — type price/value fields as nullable so `tsc` enforces guards —
  follow-up.
