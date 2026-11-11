---
title: Personal web platform design
date: 2026-11-10
status: approved
tracker: GarrettManley/websites-garrettmanley.com#1
---

# Personal web platform: garrettmanley.com hub, lab, and future sites on Cloudflare

## Context

garrettmanley.com has gone through several versions:
- 2018: Bootstrap/PHP site
- 2018: Angular 7 skeleton
- 2019: `ng-blog` on Firebase
- 2025: TypeScript placeholder in `GarrettManley/websites-garrettmanley.com`

None of them is live. A probe on 2026-11-10 showed the apex and `www` both returning a 301 from Cloudflare's edge to `github.com/GarrettManley`.

The richest existing site is the Hugo "lab" in `Workspace/site/` (hextra theme: docs, experiments dashboard, Aether guides, Hire Me page, resume PDFs). Its config targets garrettmanley.dev, but it is reachable only at `garrettmanley-lab.web.app`, deployed by a local post-commit hook. Every custom `.dev` hostname fails TLS today.

DNS for all four domains moved to Cloudflare on 2026-11-10 (`Workspace/docs/migrations/2026-11-10-squarespace-to-cloudflare.md`). Email Routing is live on `.com` and `.dev`.

Each past version was a one-off with no shared code, so every rebuild started from zero. This plan replaces that with **one platform**:
- shared, tested packages
- data kept separate from presentation
- each domain as a thin app on top

That way the hub, the lab and future sites reuse the same code.

**Decisions (Garrett, 2026-11-10):**
- **Domains:** .com is a personal hub, .dev stays the lab, and the two sites link to each other.
- **Hosting:** Cloudflare free.
- **Stack:** modern, maximizing code reuse, following SOLID and Clean Architecture, with UI decoupled from data.
- **Repo:** the platform is a monorepo, repurposing the public `websites-garrettmanley.com` repo.
- **Lab migration:** the lab is ported to the platform in Phase 2, after .com ships.
- **Future apps:** plan for g.recipes and garrettmanley.app.
- **Privacy gate:** block identifiers only. The employer name and the project name "Aether" are allowed.
- **Resume PII:** city/state plus `garrett@garrettmanley.com`, with no street address or phone.

## Goals / non-goals / anti-goals

**Goals:**
- garrettmanley.com serves a fast personal hub:
  - about
  - resume (HTML page plus PDFs)
  - projects
  - blog, seeded with the 2019 posts
  - contact
- garrettmanley.dev serves the lab from Cloudflare.
- The shared packages (domain, UI, content adapters, tooling) work for any number of apps. **Adding g.recipes or garrettmanley.app means adding `apps/<name>/` only, with no edits to shared packages.** This is the open/closed acceptance test.
- Builds are reproducible from a fresh clone, run in CI with preview URLs, and deploy per app.
- Firebase is decommissioned.

**Non-goals (v1):**
- building g.recipes or .app; only their slots are designed
- contact form (path later: Turnstile, a Worker, and the Astro Cloudflare adapter)
- CMS
- comments
- analytics beyond Cloudflare Web Analytics
- registrar transfer

**Anti-goals:**
- Leaking identifiers (private repo URLs, local paths, corporate repo directories, tracker IDs) or resume PII into a public repo or site.
- Breaking email. MX, SPF, DMARC and `_atproto` records are never touched.
- UI components that reach into data sources directly.
- Interfaces with no IO boundary and no second implementation (standard §2).
- Builds that only work on this PC.

## Technology stack (my calls unless marked)

| Concern | Choice | Why |
|---|---|---|
| Runtime | Node 24 LTS (installed) | Current LTS. |
| Workspace | **pnpm 10 workspaces + Turborepo** | Strict dependency isolation, task graph, cached `--affected` builds per app. |
| Site framework | **Astro 6, static output** | Content-first. Typed **content collections with custom loaders** are the data/UI seam. Zero JavaScript by default, with islands only where interactive (lab charts). Cloudflare acquired the Astro team in Jan 2026 and Astro stays open source and multi-target, so it is first-class on our host without lock-in. |
| Language | TypeScript `strict`, no `any` at exported boundaries | Standard §4. |
| Schemas | **Zod** (Astro's native schema layer) | One schema validates data at the boundary and yields the domain types. |
| Styling | **Tailwind v4 over CSS-variable design tokens** in `packages/ui` | Components stay theme-agnostic. Each app supplies a token theme, so g.recipes can look different without forking components. |
| Interactivity | Preact islands, only when needed | Smallest island runtime. First use is the Phase 2 experiments charts. |
| Lint/format | **Biome** | One fast tool replaces ESLint and Prettier. |
| Tests | **Vitest** (unit, integration), **Playwright** (one smoke per app) | Test pyramid (Workspace CLAUDE.md). |
| Hosting | **Cloudflare Workers Static Assets**, one Worker per app | Free unlimited static requests. A future server route uses the same Worker. |
| CI/CD | GitHub Actions + `cloudflare/wrangler-action` | Public repo, so Actions minutes are free. PRs upload versions to get preview URLs; `main` deploys affected apps. |
| Dependency updates | Dependabot (grouped, weekly) | Built in, zero setup. |

## Architecture

The repo is renamed `GarrettManley/websites` and the local clone moves `Workspace/garrettmanley.com/` to `Workspace/websites/`. The Workspace allow-list `.gitignore` already excludes it, and `~/AGENTS.md` Active project roots gets a line for it.

```text
packages/
  core/                       pure: no Astro, no fs, no fetch
    src/domain/               zod schemas + types: Resume, PublicResume, Project, Post,
                              Experiment, Adr, SiteLink; pure rules (resume variant
                              selection, PII projection, slugging, date ordering)
    src/app/                  use cases taking ports as args, e.g.
                              exportPublicResume(source: ResumeSource, sink: ContentSink)
    tests/{unit,integration}/
  content/                    adapters ring: Astro custom loaders + fs/yaml/gh readers
    src/adapters/             markdownDirLoader, jsonFileLoader, yamlResumeSource,
                              ngBlogExportReader, (phase 2) adrDirReader, experimentsReader
    tests/integration/        one per IO boundary, on fixture dirs
  ui/                         presentation only: Astro components + layouts + tokens
    src/tokens/               base tokens.css (CSS variables)
    src/components/           ResumeView, ProjectCard, PostList, SiteHeader, ...
                              props are core domain types / view models, never
                              CollectionEntry or raw files
  tools/                      CLIs (entrypoints) that wire adapters into core/app use cases
    src/sync-resume.ts        career-ops resume.yaml -> content/resume.json (PublicResume)
    src/import-ngblog.ts      one-time: ng-blog export JSON -> content/blog/*.md
    src/scrub-check.ts        privacy gate over a built dist/ against denylist.json
  config/                     shared tsconfig, biome.json, astro integration presets
apps/
  garrettmanley-com/          entrypoint: content.config.ts wires loaders+schemas;
                              pages map entries -> view models -> ui components;
                              theme.css; wrangler.jsonc; tests/e2e/smoke.spec.ts
  garrettmanley-dev/          phase 2 (lab)
  # g-recipes/, garrettmanley-app/  future: same shape, no shared-package edits
```

**Dependency rule** (standard §1): `core/domain` ← `core/app` ← `content` and `tools` adapters ← `apps/*` and `tools` CLIs. `ui` depends only on `core/domain` types. `apps` are the only place where loaders, schemas and components meet, and they contain no rules.

**Decoupling UI from data:**
- Data lives as plain files (`content/**/*.{md,json}`) validated by Zod at load time.
- A mapper in each app turns entries into view models defined in `core/domain`, and components render only those view models.
- Changing a data source (YAML to JSON, local to GitHub API) touches one adapter. Changing a look touches `ui` or a theme. Neither touches the other.

**Earned abstraction** (standard §2): ports exist only at IO boundaries:
- `ResumeSource`: filesystem
- `ContentSink`: filesystem
- the GitHub export reader: network

Pure rules are called directly. Astro's own `Loader` contract is the framework seam the content adapters implement, so we add no wrapper interface on top of it.

**Open/closed** (standard §3): a new site is a new `apps/*` folder supplying its own `theme.css`, `content.config.ts` and `wrangler.jsonc`. A new content type is a new schema in `core/domain` plus a loader registration in the app that needs it.

**Cross-site data reuse:**
- `content/shared/projects.json` (the projects registry) and `content/shared/resume.json` live at the monorepo root and are loaded by any app. The lab and .com list the same projects from one source.

**Private sources:**
- career-ops and the lab's `.ai/` sources are private or local, so CI never reads them.
- Local CLIs in `packages/tools` export sanitized data into `content/`, the output is committed, and CI builds only from committed content.
- The PII projection is enforced twice:
  - **by type:** the `PublicResume` schema has no address or phone fields, and `strict()` rejects extras
  - **by gate:** `scrub-check` runs on the built output

## Phases

**Phase 0: track and record.**
- Open an issue in the platform repo.
- Commit this design as `Workspace/docs/superpowers/specs/2026-11-10-web-platform-design.md`.
- Run `superpowers:writing-plans` for the task-level plan, then execute via `/deliver`. The architecture standard is bound as the constitution, so `review:architecture-conformance` gates the diffs.

**Phase 1: platform and garrettmanley.com.**
1. Rename the repo, set `main` as default, and clear the TypeScript skeleton and Firebase files and workflows.
2. Scaffold `packages/config`, `core`, `ui`, `content`, `tools` and `apps/garrettmanley-com`, with Turborepo tasks: `lint typecheck test build verify`.
3. In `core/domain`:
   - Resume and PublicResume schemas, plus the PII projection.
   - Variant selection: first `summaries` entry unless the yaml marks a default, plus `default_highlights`.
   - Project, Post and SiteLink schemas.
4. Tools:
   - `sync-resume`: run it and commit `content/shared/resume.json`.
   - PDFs: extract their text, check for address or phone, and regenerate them via career-ops if either is present. Commit them to `apps/garrettmanley-com/public/resume/`.
   - `import-ngblog`: fetch the export from the public `ng-blog` repo via `gh api`. Garrett reviews each post before commit.
5. `ui` components and tokens; pages for `/`, `/resume/`, `/projects/`, `/blog/` and `/contact/`. The copy is drafted, and Garrett edits it. Aether links to the lab's `/aether/`, never to the private repo.
6. `scrub-check` with `denylist.json`, covering:
   - private repo URLs and slugs used as links
   - `C:\Users\` and `/Users/` paths
   - `Workspace/Duracell*` and `malachite` references
   - `hb-[a-z0-9]+` and bare `#NNN` tracker IDs

   Lychee link check on `dist/`.
7. CI workflow, in order:
   1. install
   2. `turbo run lint typecheck test build --affected`
   3. `scrub-check` and lychee on each affected `dist/`
   4. PR: `wrangler versions upload` per affected app, with the preview URL commented on the PR; `main`: `wrangler deploy`

   Secrets: `CLOUDFLARE_API_TOKEN`, scoped to Workers Scripts:Edit for this account only, and `CLOUDFLARE_ACCOUNT_ID`. Create the token via Claude in Chrome with Garrett confirming.
8. Cutover, each step reversible:
   1. Review on `*.workers.dev`.
   2. Delete the conflicting `.com` records: the Squarespace apex A records, the `www` CNAME to `ext-sq.squarespace.com`, `_domainconnect`, and the current redirect rule to github.com.
   3. Attach Worker Custom Domains for the apex and `www`.
   4. Add a Single Redirect from `www` to the apex (301, path preserved).

**Phase 1b: lab interim on Cloudflare (minimal; Hugo is being replaced).**
- Add `site/wrangler.jsonc`. In `Workspace/publish.ps1`, replace `npx firebase-tools deploy --only hosting:documentation` with `npx wrangler deploy`. Run `scrub-check` from the monorepo build (`node ../websites/packages/tools/dist/scrub-check.js site/public`) before deploying; that's a path dependency, not a copy (standard §5).
- **Clean the current hits in the lab first:**
  - `aether-engine` appears in 6 files; fix it in `site/sync-aether-docs.ps1`.
  - Tracker IDs appear in `site/content/`; fix them in `.ai/scripts/publish_toolkit.py` and `generate_spec.py`.
  - Fix these in the generators, not in the output.
- `/hire/` becomes a stub linking to .com `/resume/`, and the PDFs are removed from the lab.
- **.dev cutover:**
  1. Attach the apex Custom Domain.
  2. Delete the Firebase wildcard `*` A record and `_acme-challenge`. This is safe because all custom `.dev` hosts fail TLS today; only `git.` is live, and it stays untouched with its redirect.
- **Skipped (my call; Phase 2 makes them moot):** committing hextra as a submodule and making the generator dates deterministic.

**Phase 2: port the lab to `apps/garrettmanley-dev`.**
- Local tools export the lab sources into `content/lab/`. Each tool is a sanitizing CLI like `sync-resume`, which replaces `publish_toolkit.py`, `generate_spec.py` and `sync-aether-docs.ps1`. The sources are:
  - `.ai/adr/`
  - the experiments data
  - the toolkit skills and scripts
  - the Aether docs
- Exports are deterministic: dates come from the source's git commit date, so unchanged sources produce byte-identical output.
- The experiments dashboard is rebuilt as Preact islands in `ui`, with the Wilson interval math in `core/domain`.
- When the lab moves, `publish.ps1`, the post-commit hook path gate, `Workspace/site/`, `firebase.json` and `.firebaserc` are retired.

**Phase 3: Firebase decommission** (after Phase 1b):
- Deploy a one-page meta-refresh redirect from `garrettmanley-lab.web.app` to `https://garrettmanley.dev` and leave it in place.
- Disable hosting on the `garrettmanley` project.
- Garrett revokes the service-account key behind `Downloads\garrettmanley-d30082e26d17.json` in GCP IAM, and the file is deleted.
- Update the migration doc's `.com` and `.dev` sections and its open items.

**Future (not in scope):** `apps/g-recipes`, `apps/garrettmanley-app`. Each is an app folder, a theme, content and a Custom Domain.

## Test design (pyramid)

**Unit** (Vitest, `packages/core/tests/unit`, the bulk of the suite):
- PII projection: the output never contains the address, phone or `keyword_pool`; the email is rewritten to `garrett@`.
- Variant selection: the default marker beats first-entry order.
- `PublicResume.strict()` rejects extra fields.
- ng-blog mapping: date preserved, slug, front-matter escaping.
- scrub matcher: each denylist class hits; employer name and "Aether" pass; the denylist file itself is excluded.
- Wilson interval (Phase 2).
- Deterministic export date (Phase 2).

**Integration** (one per IO boundary, on fixture directories):
- `yamlResumeSource`
- `ContentSink` write/read round-trip (the serialization boundary)
- `markdownDirLoader`
- `ngBlogExportReader` against a recorded fixture, not the live API

**E2E** (Playwright, one smoke per app, against `astro preview` of the built output):
- Home, resume, projects and blog return 200.
- Navigation links resolve.
- No rule checks here; those are pushed down to unit tests.

**Gates (not tests):** `scrub-check`, lychee, `astro check`, `tsc`, Biome.

## Verification

- **Fresh clone:** `git clone`, then `pnpm i`, then `pnpm turbo run lint typecheck test build verify` passes. Then `pnpm --filter garrettmanley-com exec playwright test` passes.
- **Gate proof:** planting `github.com/GarrettManley/aether-engine` in a test page fails `verify`, and so does planting a phone number in `resume.json` (schema rejection).
- **CI:** a PR comments a working preview URL, and merging to `main` deploys only the affected apps. A PR touching only `packages/ui` rebuilds every app that uses it.
- **Live:**
  - `curl -sIL https://garrettmanley.com` returns 200 with `server: cloudflare` and no redirect to GitHub.
  - `https://www.garrettmanley.com/x` returns a 301 to `https://garrettmanley.com/x`.
  - `https://garrettmanley.dev` returns 200.
  - `git.garrettmanley.dev/claude-marketplace` still redirects.
- **Email regression:** mail to `garrett@garrettmanley.com` and `jobs@garrettmanley.dev` arrives in Gmail, and the MX records are unchanged.
- **Lighthouse:** run against .com, target ≥ 95 performance, accessibility and SEO.
- **Architecture:** a `review:architecture-conformance` pass over the Phase 1 diff, with zero dependency-direction or earned-abstraction findings.
- **Workspace:** `_scripts/pre_commit_audit.ps1` and `verify_workspace.ps1` pass for Workspace-side edits (`publish.ps1`, lab generators, `AGENTS.md`).

## Critical files

- `Workspace/garrettmanley.com/`, becoming `Workspace/websites/` (the whole platform repo)
- `Workspace/publish.ps1`
- `Workspace/site/sync-aether-docs.ps1` (its redaction rules seed `denylist.json`)
- `Workspace/.ai/scripts/publish_toolkit.py`, `generate_spec.py`
- `Workspace/docs/standards/solid-clean-architecture.md` (constitution)
- `Workspace/docs/migrations/2026-11-10-squarespace-to-cloudflare.md`
- `Career/resume/resume.yaml` (read-only source)
- `~/AGENTS.md` (project roots line)
