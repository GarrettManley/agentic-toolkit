# Project Showcase (mtga-companion case study) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a reusable case-study page type on garrettmanley.com with `mtga-companion` as its first entry at `/projects/mtga-companion/`.

**Architecture:** One MDX file per case study in the shared root `content/` folder. Frontmatter is validated by a Zod schema in `@gm/core`; the body is prose that uses `@gm/ui` components supplied by the route through `<Content components={...} />`, so content files import nothing from the design system. A pure function in core decides where each project card links.

**Tech Stack:** Astro 7.4.8 (static), `@astrojs/mdx`, Zod 4, Tailwind v4, Vitest 5, Playwright, pnpm + Turborepo, Cloudflare Workers static assets.

**Spec:** `C:\Users\Garre\Workspace\docs\superpowers\specs\2026-11-19-project-showcase-design.md`

**Tracker:** websites #21 (under epic websites #1).

**Repo:** `Workspace/websites` (nested git repo, remote `GarrettManley/websites`, public). All paths below are relative to it. Work on branch `feat/project-showcase` cut from `origin/main` in a worktree at `Workspace/wt-showcase`.

## Global Constraints

- **Privacy gate (`scrub-check dist`) must pass.** No link to `github.com/GarrettManley/mtga-companion`; do not add it to `packages/tools/denylist.json`. No `#` followed by 2 to 5 digits in visible text or code. No user-home paths. No tracker ids.
- **Design system rules (Circuit Night):**
  - Flat planes only: no gradients, no blur shadows, no left-border accent cards.
  - `accent` (cyan/teal) is for interactive things only.
  - `node` (amber) appears at most once per view.
  - Sentence case for headings.
  - Numbers, dates and paths in mono; ISO dates.
  - Components use semantic `--color-*` tokens and the Tailwind utilities mapped to them, never `--brand-*` or hex.
- **Layering:** `packages/ui` imports only *types* from `@gm/core`. Components render view models and never read content.
- **Tests:** separate files under `packages/*/tests/unit` (repo convention). Unit tests only for code with conditional logic, through the public interface (`../../src/index.js`). No test duplicates a lower-level one.
- **Tooling:** Biome (line width 100) via `pnpm turbo run lint`; `astro check` runs inside `build`.
- **Commits:** conventional commits, scope `core`, `ui`, `com` or `content` (for example `feat(ui): ...`). End each message with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
- **Public name:** `mtga-companion`, lowercase everywhere it is displayed. Role line: `Architect and product owner`.
- **Schema deviation from the spec:** the spec lists "period start/end"; this plan uses a single `year` number because the page shows only a year. Widen it when a case study needs a range.

## Spike result (2026-11-19, branch `spike/mdx-root-content`, local only)

The direct approach works; no fallback is needed.

- **MDX pin:** `@astrojs/mdx` exact `8.1.3` (`pnpm --filter garrettmanley-com add -E @astrojs/mdx@8.1.3`). Its `@astrojs/markdown-satteri 0.4.7` and `@astrojs/internal-helpers 0.13.1` pins match Astro 7.4.8, so one copy of the markdown processor is installed.
- **Config:** `import mdx from "@astrojs/mdx"`; `integrations: [mdx(), sitemap()]`; `markdown: { shikiConfig: { theme: "css-variables" } }`. No alias, no hoisting.
- **Resolution:** MDX and a relative `.svg` import both resolve from root `content/case-studies/`. The SVG is inlined with `<title>`, `<desc>` and `var(--color-*)` intact (Astro strips `xmlns`).
- **Components:** `<Content components={{ Decision, Figure }} />` resolves them; the MDX imports nothing from the design system.
- **Named slots in MDX:** `<Fragment slot="proof">`, then a blank line, then the content. `<div slot="...">` also works but keeps the wrapper div. An unfilled slot renders empty, so `Decision` needs its slot-presence check.
- **Write slot tags flush-left** (found in Task 6): an indented `<Fragment slot>` whose content includes a Markdown list fails the build with `Invalid element name`. Unindented tags work with lists, paragraphs and code fences.
- **Code theme:** both the new route and existing blog posts emit `class="astro-code css-variables"` with `var(--astro-code-*)` colors.
- **Tailwind does not scan root `content/`.** A utility class used only in an MDX file produces no CSS. Content files use components and plain Markdown only, never utility classes.
- **Biome** does not check `.mdx` or `.svg`; no override needed. Write files with LF line endings (a CRLF file fails the format check).
- **Commands:** build with `pnpm turbo run build --filter=garrettmanley-com` (the bare filtered build fails on a fresh checkout because `packages/core/dist` is not built yet). If `pnpm` is not on PATH, use `corepack pnpm`.

## Review Focus

1. **Phone width.** At 375px the wide blocks (`MetricBand`, `Figure`) must not cause horizontal page scroll. Pinned by an e2e test in Task 4 (a browser is the lowest level that can see layout overflow).
2. **A project with nowhere to link.** A registry entry with no `url` and no case study must fail the build with a message naming the project. Pinned by unit tests in Task 2.
3. **A case study pointing at a project id that does not exist** (typo in frontmatter) must fail the build. Pinned by a unit test in Task 2.
4. **Light theme code colors.** Every code role must reach 4.5:1 on all three grounds in both themes. Pinned by the token test in Task 1.
5. **A decision with no recorded rejected alternative.** `Decision` must render without an empty "Rejected" row. No automated test (a slot-presence check, same idiom as `BaseLayout`); the task reviewer checks the built HTML of a fixture in Task 3.

---

### Task 1: Token-driven code colors and shared prose styles

**Files:**
- Create: `packages/ui/src/components/Prose.astro`
- Modify: `packages/ui/src/tokens/tokens.css` (both light blocks)
- Modify: `packages/ui/src/styles.css`
- Modify: `apps/garrettmanley-com/astro.config.mjs`
- Modify: `apps/garrettmanley-com/src/pages/blog/[slug].astro`
- Test: `packages/ui/tests/unit/tokens.test.ts`

**Interfaces:**
- Produces: `@gm/ui/components/Prose.astro`, no props, default slot. It wraps slotted Markdown/MDX output and restores flow spacing, headings, lists and code styling.
- Produces: CSS variables `--astro-code-*` defined on `:root` in `packages/ui/src/styles.css`, so any Shiki `css-variables` output is themed.

**Test design (unit, `tokens.test.ts`):**

| Case | Level | Why this level |
|---|---|---|
| Each of `code-keyword`, `code-string`, `code-fn`, `code-comment` on each of `bg`, `surface`, `raised` is at least 4.5:1, in dark and light | Unit | Pure arithmetic over the token file |

Mutations the test must kill: removing the light `--color-code-string` override (falls back to the `node` amber, about 3.8:1 on `surface`); setting it to `#b5661c`.

- [ ] **Step 1: Write the failing test.** In `packages/ui/tests/unit/tokens.test.ts`, add inside the existing `describe.each` block:

```ts
const CODE = ["code-keyword", "code-string", "code-fn", "code-comment"];

it.each(CODE.flatMap((fg) => GROUNDS.map((bg) => [fg, bg])))(
  "code %s on %s is at least 4.5:1",
  (fg, bg) => {
    expect(c(fg as string, bg as string)).toBeGreaterThanOrEqual(4.5);
  },
);
```

(`CODE` is declared beside `TEXT`.)

- [ ] **Step 2: Run it and confirm it fails.** `pnpm --filter @gm/ui test`. Expected: the light-theme `code-string` cases fail; all dark cases pass.

- [ ] **Step 3: Fix the token.** In `packages/ui/src/tokens/tokens.css`, add `--color-code-string: #8f4d12;` to **both** light blocks (`:root:not([data-theme="dark"])` and `:root[data-theme="light"]`). The existing "light theme blocks define identical tokens" test enforces that both got it. Leave the `:root` alias (`var(--color-node)`) as the dark value.

- [ ] **Step 4: Run the test and confirm it passes.** `pnpm --filter @gm/ui test`.

- [ ] **Step 5: Map Shiki's variables to tokens.** In `packages/ui/src/styles.css`, inside `@layer base`, add a `:root` rule:

| Shiki variable | Token |
|---|---|
| `--astro-code-foreground` | `--color-fg` |
| `--astro-code-background` | `--color-surface` |
| `--astro-code-token-keyword` | `--color-code-keyword` |
| `--astro-code-token-string`, `--astro-code-token-string-expression` | `--color-code-string` |
| `--astro-code-token-function` | `--color-code-fn` |
| `--astro-code-token-constant` | `--color-code-fn` |
| `--astro-code-token-comment` | `--color-code-comment` |
| `--astro-code-token-parameter` | `--color-fg` |
| `--astro-code-token-punctuation` | `--color-muted` |
| `--astro-code-token-link` | `--color-accent` |

- [ ] **Step 6: Turn the theme on.** In `apps/garrettmanley-com/astro.config.mjs` add `markdown: { shikiConfig: { theme: "css-variables" } }`.

- [ ] **Step 7: Extract `Prose.astro`.** Move the scoped `<style>` block from `apps/garrettmanley-com/src/pages/blog/[slug].astro` into `packages/ui/src/components/Prose.astro` verbatim, renaming `.post-body` to `.prose`; markup is `<div class="prose"><slot /></div>`. Add one rule: `pre` gets `border: var(--stroke-hair) solid var(--color-border)`. In the blog route, replace the `.post-body` div with `<div class="mt-8"><Prose><Content /></Prose></div>` and delete its `<style>` block.

- [ ] **Step 8: Verify on the blog.** `pnpm turbo run build --filter=garrettmanley-com`, then open a post under `apps/garrettmanley-com/dist/blog/`. Expected: its `<pre>` opening tag contains `var(--astro-code-` and no hex color; headings and lists keep their spacing rules in the emitted CSS.

- [ ] **Step 9: Commit.** `feat(ui): token-driven code colors and shared Prose`.

---

### Task 2: Case-study schema and the card-link rule

**Files:**
- Create: `packages/core/src/domain/case-study.ts`
- Modify: `packages/core/src/domain/project.ts`
- Modify: `packages/core/src/index.ts`
- Test: `packages/core/tests/unit/case-study.test.ts`, `packages/core/tests/unit/project.test.ts`

**Interfaces (produces):**

```ts
// case-study.ts
export const Metric: z.ZodObject<{ value: z.ZodString; label: z.ZodString }>;
export type Metric = { value: string; label: string };

export const CaseStudyFrontmatter = z.object({
  title: z.string(),
  summary: z.string(),
  project: z.string(),                 // id in content/shared/projects.json
  year: z.number().int(),
  role: z.string(),
  status: z.enum(["active", "shipped"]),
  stack: z.array(z.string()).min(1),
  metrics: z.array(Metric).min(1).max(4),
  asOf: z.coerce.date(),
  notice: z.string().optional(),
});
export type CaseStudyFrontmatter = z.infer<typeof CaseStudyFrontmatter>;

/** Display text for each status. */
export const STATUS_LABEL: Record<CaseStudyFrontmatter["status"], string>;
// { active: "in active use", shipped: "shipped" }

// project.ts
export const Project; // unchanged except: url: z.url().optional()
export type ProjectSummary = Omit<Project, "url"> & { href: string };
export type CaseStudyRef = { slug: string; project: string };

/**
 * Card view models in input order. A project with a case study links to
 * `${caseStudyBase}/${slug}/`; otherwise to its `url`.
 * @throws if a project has neither, or a case study names an unknown project id.
 */
export function summarizeProjects(
  projects: Project[],
  caseStudies: CaseStudyRef[],
  caseStudyBase: string,
): ProjectSummary[];
```

All of the above are exported from `packages/core/src/index.ts` (types with `export type`).

**Test design (all unit, through `../../src/index.js`):**

| Case | Expected |
|---|---|
| `summarizeProjects`: project has a URL and a case study | `href` is `/projects/<slug>/` (case study wins) |
| project has only a URL | `href` is that URL; the result has no `url` key |
| project has neither | throws; message contains the project id |
| a case study names an id not in `projects` | throws; message contains that id |
| order | output order equals input order |
| `CaseStudyFrontmatter`: five metrics | `safeParse(...).success` is `false` |
| `CaseStudyFrontmatter`: `asOf: "2026-11-12"` | parsed `asOf` is a `Date` |

Mutations to kill: preferring `url` over the case study; dropping either throw; `.max(4)` changed to `.max(5)`.

- [ ] **Step 1: Write the failing tests** for the seven cases above. Use `caseStudyBase = "/projects"`. Fixture project: `{ id: "a", name: "A", summary: "s", tags: [], featured: false }` plus `url` where the case needs one.
- [ ] **Step 2: Run them and confirm they fail.** `pnpm --filter @gm/core test`. Expected: import errors for the new names.
- [ ] **Step 3: Implement** `case-study.ts`, the `project.ts` changes and the exports.
- [ ] **Step 4: Run and confirm they pass.** `pnpm --filter @gm/core test`, then `pnpm --filter @gm/core build` if the package has a build step (the app consumes its `dist`).
- [ ] **Step 5: Commit.** `feat(core): case-study schema and project card-link rule`.

---

### Task 3: Case-study components

**Files:**
- Create: `packages/ui/src/components/Breadcrumb.astro`, `MetricBand.astro`, `Figure.astro`, `Decision.astro`, `TagList.astro`
- Modify: `packages/ui/src/styles.css` (`.measure-wide`)
- Modify: `packages/ui/src/components/ProjectCard.astro` (use `TagList` for its tags; no visual change)

**Interfaces:**
- Consumes: types `Metric`, `SiteLink` from `@gm/core` (Task 2).
- Produces:

| Component | Props | Slots | Renders |
|---|---|---|---|
| `Breadcrumb` | `trail: SiteLink[]` (last item is the current page) | none | `<nav aria-label="Breadcrumb">` with an `<ol>`; a leading `~`; ` / ` separators in `accent`, `aria-hidden`; links for all but the last item; the last item is plain text with `aria-current="page"`. Mono, small, `muted`. |
| `TagList` | `tags: string[]`, `label?: string` (default `"Tags"`) | none | The `<ul aria-label>` of mono tags that `ProjectCard` renders today, moved verbatim |
| `MetricBand` | `metrics: Metric[]` | none | A `<dl class="measure-wide">`: two columns below `sm`, four from `sm` up; each cell is a `<div>` with the value in `<dd>` (mono, `text-h3`, `fg`) and the label in `<dt>` (small, `muted`); hairline `border` above and below. Use `flex-col-reverse` or source order so the value reads first visually while `dt` precedes `dd` in the DOM. |
| `Figure` | `caption: string` | default | `<figure class="measure-wide">` with the slot inside a block that scrolls horizontally if its content is wider, and a small `muted` `<figcaption>` |
| `Decision` | `n: number`, `title: string` | `chose`, `why`, `rejected` (optional), `proof` | A `<section>`; an `<h3>` with the number as a two-digit mono prefix (`01`) in `muted` and the title; a `<dl>` with one row per filled slot, labels `Chose`, `Why`, `Rejected`, `Proof` in the `text-eyebrow` style (uppercase, mono, `muted`). The `rejected` row is rendered only when `Astro.slots.has("rejected")`. Rows are separated by hairline `border`; no card fill, no left accent border. |

- `.measure-wide` (in `packages/ui/src/styles.css`, `@layer base`):

```css
.measure-wide {
  --_w: min(var(--measure-wide), 100vw - 2 * var(--space-4));
  width: var(--_w);
  margin-inline-start: calc(50% - var(--_w) / 2);
}
```

It works because `<main>` is centered and capped at the prose measure, so 50% is the column's midpoint.

**Tests:** none. These components have no branching beyond one slot-presence check (the idiom `BaseLayout.astro` already uses untested). `astro check` is the gate; Review Focus item 5 is checked by the reviewer in Task 4's built page.

- [ ] **Step 1: Add `.measure-wide`** to `styles.css`.
- [ ] **Step 2: Create the five components** to the table above.
- [ ] **Step 3: Switch `ProjectCard` to `TagList`.**
- [ ] **Step 4: Verify.** `pnpm turbo run lint typecheck --filter=@gm/ui` passes.
- [ ] **Step 5: Commit.** `feat(ui): case-study components (Breadcrumb, MetricBand, Figure, Decision, TagList)`.

---

### Task 4: MDX collection, the route, and a skeleton entry

**Files:**
- Modify: `apps/garrettmanley-com/package.json`, `apps/garrettmanley-com/astro.config.mjs` (MDX integration, per the spike result)
- Modify: `apps/garrettmanley-com/src/content.config.ts`
- Create: `apps/garrettmanley-com/src/data/case-studies.ts`
- Create: `apps/garrettmanley-com/src/pages/projects/[slug].astro`
- Create: `content/case-studies/mtga-companion.mdx` (final frontmatter, skeleton body)
- Test: `apps/garrettmanley-com/tests/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: `CaseStudyFrontmatter`, `STATUS_LABEL` (Task 2); `Breadcrumb`, `TagList`, `MetricBand`, `Figure`, `Decision`, `Prose` (Tasks 1 and 3).
- Produces: collection `caseStudies` (`glob({ pattern: "*.mdx", base: "../../content/case-studies" })`, schema `CaseStudyFrontmatter`); `CASE_STUDY_BASE = "/projects"` and `getCaseStudies()` in `src/data/case-studies.ts`; the route `/projects/<entry.id>/`.

**Frontmatter for `content/case-studies/mtga-companion.mdx`** (values re-verified in Task 6 before merge):

```yaml
title: mtga-companion
summary: A local tracker that turns a game log into statistics you can trust.
project: mtga-companion
year: 2026
role: Architect and product owner
status: active
stack: [Rust, SQLite, MCP, egui, Windows]
metrics:
  - { value: "2,291", label: "tests on the full gate" }
  - { value: "1820 → 26 ms", label: "slowest query, after the fix" }
  - { value: "62 → 1.2 MB", label: "a session log, archived" }
  - { value: "15", label: "read-only tools over MCP" }
asOf: 2026-11-12
```

**Route layout, top to bottom** (`<Page title={title} description={summary}>`):

1. `<Breadcrumb trail={[{ label: "projects", href: "/projects/" }, { label: entry.id, href: "" }]} />`
2. `<h1 class="text-h1">` title; a mono `muted` line: `{year} · {role} · {STATUS_LABEL[status]}`; summary as `text-lead`.
3. `<TagList tags={stack} label="Stack" />`
4. `<MetricBand metrics={metrics} />`
5. `<Prose><Content components={{ Decision, Figure }} /></Prose>`
6. A closing line with links to `/resume/` and `/contact/`.
7. Small `muted` text: `Numbers as of {asOf as YYYY-MM-DD}.` and, when present, `notice`.

**Test design:**

| Case | Level | Why this level |
|---|---|---|
| The first case-study route returns 200 | E2E (existing "core routes return 200" test; add `firstCaseStudyPath()`, mirroring `firstPostPath()` over `content/case-studies/*.mdx`) | Routing only exists in the built site |
| At a 375px-wide viewport the case-study page has no horizontal overflow: `document.documentElement.scrollWidth <= clientWidth` | E2E (new test) | Layout overflow is only observable in a browser; this guards `.measure-wide` |

Mutation to kill: changing `.measure-wide`'s `100vw - 2 * var(--space-4)` to `100vw` must fail the overflow test.

- [ ] **Step 1: Write the two e2e changes** in `smoke.spec.ts`.
- [ ] **Step 2: Run and confirm they fail.** `pnpm turbo run build --filter=garrettmanley-com && pnpm --filter garrettmanley-com e2e`. Expected: `content/case-studies has no entries` (or a 404).
- [ ] **Step 3: Add MDX** exactly as the spike result records (version pin, any alias).
- [ ] **Step 4: Register the collection, add `case-studies.ts`, the route, and the skeleton MDX** (frontmatter above; body: one paragraph, one `<Decision n={1} title="Skeleton">` using the slot syntax from the spike result with a fenced code block in `proof` and **no** `rejected` slot, and one `<Figure caption="Skeleton">` around a paragraph).
- [ ] **Step 5: Build and run e2e; confirm both pass.** Also confirm in `dist/projects/mtga-companion/index.html` that no "Rejected" label is rendered (Review Focus 5).
- [ ] **Step 6: Run the gates.** `pnpm turbo run lint typecheck test verify`.
- [ ] **Step 7: Commit.** `feat(com): case-study collection and /projects/[slug] route`.

---

### Task 5: Link project cards to case studies

**Files:**
- Modify: `content/shared/projects.json`
- Modify: `apps/garrettmanley-com/src/data/projects.ts`
- Modify: `packages/ui/src/components/ProjectCard.astro`
- Modify: `apps/garrettmanley-com/src/pages/projects.astro`

**Interfaces:**
- Consumes: `summarizeProjects`, `ProjectSummary` (Task 2); `getCaseStudies`, `CASE_STUDY_BASE` (Task 4).
- Produces: `getProjects()` and `getFeaturedProjects()` now return `Promise<ProjectSummary[]>`; `ProjectCard` takes `project: ProjectSummary` and links its heading to `project.href`.

**Registry entry**, inserted **first** in `content/shared/projects.json` (no `url`):

```json
{
  "id": "mtga-companion",
  "name": "mtga-companion",
  "summary": "A local tracker for MTG Arena that turns the game's log into statistics you can trust, with a live overlay and a query surface for Claude Code over MCP.",
  "tags": ["rust", "sqlite", "mcp"],
  "featured": true
}
```

`projects.astro` intro becomes: "What I build outside the day job. Projects with a case study link to a write-up of how they were designed."

**Tests:** none new. The linking rule is unit-tested in Task 2; the link check (Lychee, in CI) catches a dead card link; the home and projects routes are already in the e2e 200 list.

- [ ] **Step 1: Make the four changes.**
- [ ] **Step 2: Verify.** `pnpm turbo run build --filter=garrettmanley-com`; in `dist/projects/index.html` and `dist/index.html` the mtga-companion card's link is `/projects/mtga-companion/`; the other cards keep their external links. Then `pnpm turbo run lint typecheck test verify` and the e2e suite.
- [ ] **Step 3: Commit.** `feat(com): link project cards to case studies; add mtga-companion`.

---

### Task 6: Write the mtga-companion case study

**Inputs:** the spec's page outline, decision table and privacy rules; the verified evidence pack, kept in the project's private repo (never copied into the websites repo).

**Files:**
- Modify: `content/case-studies/mtga-companion.mdx` (replace the skeleton body; correct frontmatter metrics to the verified values)
- Create: `content/case-studies/mtga-companion.architecture.svg`

**Content rules:**
- First person, plain verbs, no hype. Target 900 to 1,200 words of body.
- Sections, in order: `## Architecture` (one paragraph, the figure, a short list that is the diagram's text equivalent), `## Decisions` (five `Decision` blocks), `## How it was built` (about 100 words; names Claude Code once), `## What's next` (the experiment loop, stated as planned).
- Every number and every "Rejected" comes from the evidence pack. A claim the pack marks NOT FOUND is cut or reworded, never kept. A decision whose pack entry says "none recorded" omits the `rejected` slot and is listed in the PR description for Garrett.
- Two or three code or SQL excerpts at most, each under 25 lines, taken from the pack's screened candidates.
- `notice` frontmatter: the Fan Content Policy wording fetched from Wizards' current policy page.

**Diagram rules** (`mtga-companion.architecture.svg`):
- `role="img"`, `<title>` and `<desc>`; laid out top-down in a `viewBox` about 360 units wide so labels stay at least 12px at a 343px render width.
- Strokes and fills only from `var(--color-*)`; drawn on `--color-bg`; boxes filled `--color-surface` with `--color-border` strokes; edges at `--stroke-trace` in `--color-control`; text in `--color-fg` or `--color-muted`, font inherited.
- `--color-node` is used exactly once: the raw store, the single source of truth.
- Nodes: Player.log → capture (single writer) → raw store → parser → derived tables → views; branches from the store to the live overlay (separate read-only process) and from the views to the MCP tools → Claude Code.

- [ ] **Step 1: Correct the frontmatter metrics** against the evidence pack.
- [ ] **Step 2: Draw the SVG.**
- [ ] **Step 3: Write the body.**
- [ ] **Step 4: Build and run the gates.** `pnpm turbo run lint typecheck test verify` and the e2e suite.
- [ ] **Step 5: Claims pass.** Check each number in `dist/projects/mtga-companion/index.html` against the pack; list them in the PR description with their status.
- [ ] **Step 6: Excerpt pass.** Read each code block against the spec's trip list by eye.
- [ ] **Step 7: Commit.** `feat(content): mtga-companion case study`.

---

### Task 7: Pull request, preview review, merge

- [ ] **Step 1: Push `feat/project-showcase` and open a PR against `main` in `GarrettManley/websites`** (not the Workspace repo). Body: `Closes #21`, the claims list from Task 6, any decision missing a "Rejected", and what Garrett needs to review. End with the Claude Code attribution line.
- [ ] **Step 2: Wait for CI to finish green.** Do not merge on red or pending.
- [ ] **Step 3: Check the preview URL** from the CI comment: 375px and desktop, light and dark, keyboard order, the diagram legible on a phone; run Lighthouse on `/projects/mtga-companion/` and record the four scores in the PR.
- [ ] **Step 4: Garrett reviews the prose on the preview.** Apply his edits.
- [ ] **Step 5: Merge after his approval;** confirm the deploy and that the live route, the projects card and the home card all work.
- [ ] **Step 6: Follow-ups.** Open the link-preview (Open Graph) PR per the spec's Phase 2; note the third copy of the ISO-date formatting on websites issue 15's Rule of Three watch; update the platform spec's stale "Astro 6" line.
