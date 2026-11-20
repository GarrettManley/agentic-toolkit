# Project showcase on garrettmanley.com (mtga-companion first)

Tracker: websites #21 (showcase), under the platform epic websites #1.

## Context

garrettmanley.com lists projects as cards that link out. Nothing on the site shows *how* Garrett designs a system, which is what a hiring manager wants to judge and what a recruiter needs keywords for. Garrett is in an active job search, so this page will be sent to people directly.

The showcase adds case-study pages to the site. mtga-companion goes first because it has the strongest architecture story and its repo is private, so nobody can see that work today. The page is a taste of architectural ability. It is not the project's documentation.

## Decided with Garrett

| Question | Decision |
|---|---|
| Source access | The page stands alone. The mtga-companion repo stays private; no links to it. Proof is carried on the page: a diagram, curated excerpts, measured numbers. |
| AI-agent delivery | One short "How it was built" section. The page is about the system. |
| Page shape | Layered single page: skim layer first (recruiter), decisions below (hiring manager). |
| Build approach | One MDX file per case study. Validated frontmatter for the skim layer, free prose body using design-system components. |
| Visual language | The Circuit Night design system, extended where case studies need new pieces. |
| Public name | Keep `mtga-companion` for the title and URL, set in lowercase like a project codename, with the fan-content notice. The privacy gate is not changed for it. |
| Role line | "Architect and product owner". |
| Timing | As soon as possible: one pull request with only what the page needs. Link-preview tags and the design-system book sync follow once the page is live. |

## My calls (correct any of these)

- **Reusable page type, not a one-off.** Aether and the marketplace should later need only a content file and a diagram.
- **Hand-drawn SVG architecture diagram** colored from design tokens, not Mermaid. It is the centerpiece, follows light and dark themes, and adds no script weight. Build-time Mermaid waits until a page needs many diagrams.
- **Repo first, then the design-system book.** The book says `websites/packages/ui` is canonical. New pieces land in the repo, then get mirrored to the "gm design system" artifact.
- **Every public claim is sourced.** Each number and each "rejected alternative" maps to a file in the mtga-companion repo (ledger below) and is re-read at the source before it is written. The page carries an "as of" date because Sprint 8 is in flight.
- **Garrett reviews all prose on the PR preview before merge.** The page makes professional claims in his voice.
- **mtga-companion becomes the first featured project,** so it shows on the home page. That pushes the marketplace card off the home page's top three (it stays on `/projects/`).
- **Sections without numbers are sourced too.** "How it was built", "What's next" and each decision's "Why" are drafted from the project's spec and retrospectives (ledger rows below), then reviewed by Garrett. "How it was built" names Claude Code once, plainly; the tool already appears on the page because the statistics are served to it over MCP.
- **Content drafting runs alongside the platform work,** not after it. It depends only on the mtga-companion repo.
- **Link previews get a title and description** (Open Graph tags; the site has none today) in a small follow-up PR right after launch. A preview image comes later.
- **The blog's body styles move into the design system** as a shared prose component. The repo's "Rule of Three" note would say duplicate, but it is a verbatim move and the code-color change edits the same rules in the same PR.
- **Code colors: light-theme string color gets its own darker amber.** Today it aliases the `node` amber, which is 3.8 to 4.3:1 as text on the light grounds, below the 4.5:1 bar. The contrast test is extended to cover code roles.
- **No overlay screenshot in v1** (see "Needs Garrett").

## Goals, non-goals, anti-goals

**Goals**
- A recruiter gets stack, scale and status from the first screen in under a minute.
- A hiring manager can read five decisions, each with what was chosen, why, what was rejected and the proof.
- The second case study costs one content file and one diagram.
- The site keeps its Lighthouse bar (99/100/96/100 live; spec target is 95+).

**Non-goals**
- Documentation, setup guides, API reference.
- Interactive diagrams, client-side scripts, Mermaid.
- Making the mtga-companion repo public.
- Case studies for other projects (follow-up, content only).

**Anti-goals** (failure even if it ships)
- A number on the page that the repo does not back.
- Describing planned work (the experiment loop) as shipped.
- A leak past the privacy gate: repo links, issue numbers, local paths, player identifiers.
- A page that reads as AI-tool marketing instead of system design.

## Approaches considered

1. **Structured header, free body (chosen).** MDX per case study; typed frontmatter; prose body with components. Enforces structure where readers skim, leaves freedom where they read. Cost: adds MDX; the body's shape is held by components and review, not the schema.
2. **Pure data, rigid template.** Everything validated, one template. Closest to the platform spec's view-model rule, but prose and code in data files are awkward and unusual stories force schema changes.
3. **Plain Markdown like the blog.** Cheapest; nothing enforces the layered shape, so later case studies drift and the skim layer is hand-built each time.

Dropped early: client-side Mermaid (script weight against the Lighthouse bar) and a separate showcase site (splits readers from the resume).

## The page

Route: `/projects/mtga-companion/`

```
~ / projects / mtga-companion

mtga-companion       2026 · architect and product owner · in active use
A local tracker that turns a game log into statistics you can trust.

[Rust] [SQLite] [MCP] [egui] [Windows]

| 2,291 tests | 1820 → 26 ms query | 62 → 1.2 MB fixtures | 15 tools over MCP |

ARCHITECTURE      one SVG: log → capture → raw store → parsed → views
                  branches: live overlay (read-only process), MCP tools
DECISIONS
  1 The log is the only source of truth
  2 Rebuild equals incremental
  3 A regression every gate missed
  4 Hidden information has no field
  5 The overlay is a separate read-only process
HOW IT WAS BUILT  ~100 words
WHAT'S NEXT       the experiment loop, stated as planned
[Resume] [Contact]
Fan-content notice · numbers as of <date>
```

### Decision blocks

Each has four parts: **Chose / Why / Rejected / Proof**. Proof is a number, a named test, or a short excerpt.

| # | Decision | Proof to show |
|---|---|---|
| 1 | Every log byte is stored exactly; everything else is derived from it | Export of an ingested archive reproduces the archive byte for byte; 62 MB session stored as 1.24 MB |
| 2 | The parser is a pure, versioned function of the raw store, so a full rebuild must equal incremental parsing | The tested invariant; full rebuild of 53,082 entries in about 2 s |
| 3 | A fix made card queries about 3x slower while every gate stayed green; performance is now guarded by measured SQLite work against a committed baseline | Query 1819.8 ms → 26.2 ms; the two guard tests; a short SQL before/after excerpt |
| 4 | The live snapshot has no field that could hold the opponent's hidden cards | Deleting opponent actions from the fixture leaves every derived table identical |
| 5 | The overlay is its own read-only process, so a GUI crash cannot stop capture | Read-only scan test; 72.5 MB and 0.39% CPU after choosing the lighter renderer |

### Claims ledger (kept in the spec, not published)

> **Superseded 2026-11-19 by the verified evidence pack**, which is kept in the project's private repo and was read from its main branch. The pack qualifies several rows below, and the page was written from the pack, not from this table:
> - **2,291 tests** is the last recorded gate run, 40 commits before the tip.
> - **1819.8 → 26.2 ms** was a pre-merge defect measured at 73 matches, so it is not a headline.
> - **62 → 1.24 MB** is a scrubbed test fixture, not how the product stores data.
> - **Rebuild 2.023 s** is from October; production now takes about 10 s for 151,417 entries.
> - **`dead_cards` 327 → 93.9 ms** mixes two stores and includes later optimisations.
> - **72.5 MB / 0.39%** is a spike figure; the shipped overlay plus capture measured 121.0 MiB / 1.78%.
>
> The page's headline numbers are now 2,291 / 151,417 / 10.6 s / 15.

Each claim was traced to a source in the project's private repo and re-read there when the content was written. The exact sources (files, tests, documents) are recorded in the private evidence pack, not here; this table keeps only the claim and the kind of source.

| Claim | Kind of source |
|---|---|
| 2,291 tests on the full gate | Sprint demo record |
| `matchups` 1819.8 ms → 26.2 ms | Performance tables in the format documentation |
| 61,980,431 bytes → 1,240,471 bytes | A recorded test fixture's manifest |
| 15 read-only MCP tools | Source code |
| Rebuild: 2.023 s for 53,082 entries | Format documentation |
| About 3x regression; `dead_cards` 327 ms → 93.9 ms | Retrospective |
| Guards: a SQLite-work budget test (+25%) and query-plan tests | Test suite |
| A test that removes opponent actions and requires identical derived tables | Test suite |
| Renderer choice: 72.5 MB / 0.39% CPU vs 154 MB | Design spec amendments |
| Schema v1 → v6, 14 views | Source code |
| Each decision's "Why" and "Rejected" | Design spec: its decision table and later amendments |
| "How it was built": test design first, per-task review, final adversarial review, sprint count | Retrospectives, one per sprint |
| "What's next": the experiment loop is planned, not built | Design spec and the project's summary notes |
| Header: status "in active use", year | Latest retrospective; commit dates |

Rule for "Rejected": only alternatives the repo records (spec decision table, amendments, rulings). Where none is recorded, Garrett supplies it or that part is dropped for that decision.

### Privacy and IP rules for the content

- No link to the private repo; no `#123` references; no deck names, rank numbers or player identifiers.
- Known trips for the privacy gate on this page:
  - the Arena log path written with a user-home prefix (write it with `%USERPROFILE%`)
  - any `#NN` in code, including Rust format specs like `{:#04x}` and hex colors
  - tracker ids in code comments
  - a card name containing "Malachite" (the corporate-directory rule is case-insensitive)
- **Code excerpts need hand review.** The gate sees highlighted code as split-up markup, so an identifier or path broken across tokens can pass silently. Do not rely on the gate for excerpts.
- Add the Wizards of the Coast Fan Content Policy notice; fetch the required wording from the current policy page when writing.
- In MDX, `<` and `{` in prose must sit inside backticks (for example `Vec<T>`).

## Design-system additions (`websites/packages/ui`)

| Piece | Purpose |
|---|---|
| `Breadcrumb` | Terminal-slash trail (`~ / projects / mtga-companion`), slashes in `accent`, last item marked current |
| `MetricBand` | One to four numbers with labels, mono numerals, wide |
| `Figure` | Wide breakout, caption, slot for inline SVG |
| `Decision` | Numbered; named slots for chose / why / rejected / proof |
| `Prose` | The blog's body styles, moved verbatim |
| `.measure-wide` utility | Breaks a block out of the 70ch column to `--measure-wide` without changing the layout |
| Code theme | Build-time highlighting mapped to `--color-code-*` in both themes; also fixes blog code blocks, which are hard-coded dark today |
| Diagram vocabulary | Written rules for hand-drawn diagrams: box, store, process, trace edge, where `node` amber may appear; draw on `bg`, not `surface` |

All use existing tokens except the light-theme string color. Stack tags reuse the tag markup already in `ProjectCard`.

## Implementation outline

All paths are under `C:\Users\Garre\Workspace\websites\`. Tests follow the repo convention (`packages/*/tests/unit`), which keeps them out of implementation files.

### Phase 0: tracker, spec, spike

1. Open a websites issue for the showcase; re-point this plan and the spec at it.
2. Save this design as `C:\Users\Garre\Workspace\docs\superpowers\specs\2026-11-19-project-showcase-design.md` (beside the platform spec) and produce the task-level plan with per-task test designs.
3. **Spike on a throwaway branch** (the one real technical risk). MDX files live in the shared root `content/` folder, outside the app. Unlike the blog's Markdown, MDX is imported as a module, and the repo's package layout does not hoist `astro` to the root. Astro's own dedupe setting should make it resolve, but only a build proves it.
   - Add `@astrojs/mdx` pinned to exact `8.1.3` (it shares Astro 7.4.8's markdown-processor pins; newer versions would install a second copy). Confirm the pin against the registry first.
   - Fixture MDX with: a component supplied through `<Content components={{…}} />`, a fenced code block inside a named slot, and a relative `.svg` import.
   - Pass means: the build succeeds; the HTML has the component output, code colored by CSS variables, and an inline `<svg>` with its `<title>`; one copy of the markdown processor is installed.
   - Fallbacks, in order: a Vite alias for Astro's JSX and asset runtimes; move case-study MDX into the app; hoist `astro` in `pnpm-workspace.yaml`.

### Phase 1: the case study (one PR, two tracks in parallel)

**Track A, platform** (in the websites repo, after the spike passes):

| Step | Files | Test |
|---|---|---|
| `Prose` component; blog route uses it | `packages/ui/src/components/Prose.astro` (new), `apps/garrettmanley-com/src/pages/blog/[slug].astro` | None: no conditional logic |
| Code colors from tokens (the excerpts need them in both themes) | `apps/garrettmanley-com/astro.config.mjs` (`markdown.shikiConfig.theme: "css-variables"`), `packages/ui/src/styles.css` (map `--astro-code-*` to tokens), `packages/ui/src/tokens/tokens.css` (light string color, both light blocks) | Unit: extend `packages/ui/tests/unit/tokens.test.ts` with code roles at 4.5:1 |
| Schema | `packages/core/src/domain/case-study.ts` (new): `Metric`, `CaseStudyFrontmatter` (title, summary, project id, stack, 1 to 4 metrics, role, period start/end, status `active` or `shipped`, optional notice, as-of date); export from `packages/core/src/index.ts` | Unit: `packages/core/tests/unit/case-study.test.ts`, five metrics rejected |
| Card-link rule | `packages/core/src/domain/project.ts`: `url` becomes optional; add `summarizeProjects(projects, caseStudies, base)` returning cards with an `href`. It throws when a project has neither a URL nor a case study, and when a case study names an unknown project | Unit: `packages/core/tests/unit/project.test.ts`: case study wins, URL fallback, both throws |
| Components | `packages/ui/src/components/{Breadcrumb,MetricBand,Figure,Decision}.astro` (new); `.measure-wide` in `packages/ui/src/styles.css` | None: no conditional logic. `astro check` is the gate |
| Collection and route | `apps/garrettmanley-com/src/content.config.ts` (register `caseStudies`), `apps/garrettmanley-com/src/pages/projects/[slug].astro` (new, mirrors the blog route), `astro.config.mjs` and `package.json` (MDX) | E2E: add `firstCaseStudyPath()` beside `firstPostPath()` in `apps/garrettmanley-com/tests/e2e/smoke.spec.ts` |
| Card linking | `content/shared/projects.json` (add mtga-companion, featured, first, no URL), `apps/garrettmanley-com/src/data/projects.ts` (call `summarizeProjects`), `packages/ui/src/components/ProjectCard.astro` (link uses `href`), `apps/garrettmanley-com/src/pages/projects.astro` (intro line) | None new: the rule is tested in core |

**Track B, content** (starts immediately; reads only the mtga-companion repo until the route exists):

1. Verify every ledger row at its source.
2. Draft the five decisions, "How it was built" and "What's next".
3. Draw the architecture diagram: `content/case-studies/mtga-companion.architecture.svg` with `role="img"`, `<title>`, `<desc>`, and a prose equivalent beneath. Lay the pipeline out top-down so labels stay legible at 375px wide.
4. Assemble `content/case-studies/mtga-companion.mdx` once the route exists; add the fan-content notice and the as-of date.

Gates for Track B: the privacy gate, the link check, and hand review of every excerpt.

### Phase 2: right after launch

- **Link-preview tags** (small PR): `apps/garrettmanley-com/src/layouts/Page.astro`, through the existing `head` slot, reusing `canonical`. No test: no conditional logic. Check with LinkedIn Post Inspector.
- **Design-system book:** mirror the repo into the "gm design system" artifact: the new components (guidelines and a preview each), the diagram vocabulary, the code-color change in `tokens.json`. Publishing to the artifact needs Garrett's approval at that point.

### Follow-ups, not in this plan

- Preview image for shared links.
- Overlay screenshot.
- Case studies for Aether and the marketplace.

## Delivery

- Work happens in the nested `websites` repo; branches come off `origin/main` (the local `origin/HEAD` still points at a stale `development` branch). PRs target `websites`, not the Workspace repo.
- One PR for the case study, then the small link-preview PR. Each waits for green CI before merge; a red PR was merged here once.
- CI posts a preview URL on the PR. Garrett reviews the case-study prose there.
- Merge to `main` deploys automatically.
- Update the stale "Astro 6" line in the platform spec while there.

## Verification

- **Local gates** (from the websites root): `pnpm turbo run lint typecheck test verify`, then `pnpm --filter garrettmanley-com e2e`.
- **Built HTML:** blog and case-study `<pre>` blocks carry no hex colors; the diagram is inline with its title.
- **Preview URL, by eye:** 375px and desktop; light and dark; keyboard through the page; the diagram's labels readable on a phone.
- **Lighthouse** on the preview URL for the new page: at or above the live bar.
- **Claims pass:** every number on the page checked against the ledger source; every "Rejected" traced to a recorded decision.
- **Excerpt pass:** every code block read against the trip list above.
- **After deploy:** `/projects/mtga-companion/` returns 200 on the live site; the projects card and home card link to it. After the Phase 2 PR, LinkedIn Post Inspector shows title and description.

## Needs Garrett

1. **Prose review** on the PR preview before merge.
2. **Rejected alternatives** for any decision where the repo records none.
3. **Overlay screenshot (optional follow-up):** a capture from a fixture replay, not over the live game, would be the strongest "this is real" proof. It needs an attended session.
4. **Approval to publish** the design-system book update in Phase 2.
