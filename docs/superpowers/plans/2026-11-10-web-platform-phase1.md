# Web Platform Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `GarrettManley/websites-garrettmanley.com` into the `websites` monorepo and ship garrettmanley.com on it via CI to Cloudflare Workers Static Assets. The site has a resume, projects, a blog and a contact page.

**Architecture:**
- **Rings** (Workspace standard §1):
  - `packages/core`: pure Zod schemas, types and rules.
  - `packages/tools`: sync/import/scrub CLIs, each with its adapters.
  - `packages/ui`: Astro components that take only core types.
  - `apps/garrettmanley-com`: composition only. Astro's built-in `glob()`/`file()` loaders read the committed `content/`.
- **Private sources** (career-ops) are exported locally into committed, sanitized content. CI never reads them.

**Tech Stack:**
- Node 24, pnpm 12.18.0, Turborepo 2.6.x
- Astro 7.4.x (static), TypeScript strict, Zod 4 (`^4.6.7`, the same range Astro 7.4.10 depends on)
- Tailwind v4.3 via `@tailwindcss/vite`, `@astrojs/sitemap`
- Biome 2.x, Vitest 4.x, Playwright 1.65
- wrangler 4.x, lychee

**Spec:** `C:\Users\Garre\Workspace\docs\superpowers\specs\2026-11-10-web-platform-design.md` (tracker GarrettManley/websites-garrettmanley.com#1, to be renamed `GarrettManley/websites` in Task 1).

**Deviations from spec (my calls, made while writing this plan):**
1. **No `packages/content` in Phase 1.** Astro's built-in `glob()`/`file()` loaders already are the filesystem adapters. Writing wrappers would be an unearned abstraction (standard §2). The package arrives in Phase 2 if the lab exporters need shared adapters.
2. **Resume variant selection and PII projection stay in career-ops Python** (`build_data`), behind a new `--public` flag. Re-implementing them in TypeScript would duplicate a utility (standard §5). The platform enforces PII by type: the `PublicResume` schema is `.strict()` with no phone or address fields. `scrub-check` adds a second gate.
3. **Astro 7.4, not "Astro 6".** 7.x is the current stable release; the spec predates checking.

## Global Constraints

- **Corporate isolation:** never read, grep or reference `Workspace/Duracell*` or `Workspace/malachite/` in code, content, prompts or fixtures.
- **Public repo:** nothing committed may contain a phone number, street address, local path (`C:\Users\…`, `/Users/…`), a private repo URL, or tracker IDs (`hb-…`, bare `#NNN` refs to internal issues).
- **Allowed text:** the employer name "Duracell" and the project name "Aether" are allowed in content.
- **Resume contact block:** `basics.location` (city/state), email `garrett@garrettmanley.com`, the site URL and LinkedIn. Nothing else.
- **Email records:** MX, SPF, `_dmarc` and `_atproto` records on garrettmanley.com are never modified.
- **TypeScript:** `strict: true`, `noUncheckedIndexedAccess: true`, and no `any` at exported boundaries.
- **Tests:** sibling `tests/` trees only; never inline in implementation files.
- **Imports point inward:** `apps/*` → `ui` / `tools` → `core`. `core` imports only `zod`, and `ui` imports `core` types only.
- **Line endings:** `.gitattributes` uses `* text=auto eol=lf`, and CI runs on `ubuntu-latest`.
- **Commits:** end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Platform repo commits reference `#1`.

## Review Focus

1. **Scrub false positives:** CSS hex colors (`#ff0000`) and `href="#top"` anchors in built HTML must not trip the tracker-ID rule. That rule scans extracted text only (Task 5 test `ignores hex colors and anchors`).
2. **Unknown URL:** a request for a missing path returns the site's 404 page with status 404, not a 200 home page (Task 7 e2e `unknown route is 404`).
3. **www deep links:** `https://www.garrettmanley.com/blog/x?y=1` lands on the apex with the path and query preserved (Task 9 verification).
4. **Fresh clone on Linux:** content path casing and CRLF must not break the CI build (Task 1 `.gitattributes`; Task 8 runs on ubuntu).
5. **Special characters in resume text:** an `&`, `<` or a quote in a highlight renders literally, never as markup. Astro's escaping handles this, provided no component uses `set:html` on resume data (Task 6 constraint; Task 7 e2e asserts `&` renders).

---

### Task 1: Repo reset and monorepo scaffold

**Files:**
- Delete:
  - `.firebaserc`, `firebase.json`, `remoteconfig.template.json`
  - `.github/workflows/firebase-hosting-*.yml`
  - `public/`, `src/`, `tsconfig.json`, `package-lock.json`
  - `.vscode/launch.json`
- Keep: `LICENSE.md`, `README.md` (rewrite)
- Create:
  - `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `biome.json`
  - `.gitattributes`, `.gitignore`, `.nvmrc`
  - `packages/config/tsconfig.base.json`, `packages/config/package.json`
- Modify: `C:\Users\Garre\AGENTS.md` (Active project roots)

**Interfaces:**
- Produces:
  - Root scripts `lint`, `typecheck`, `test`, `build`, `verify`, `e2e`, `deploy`, `preview`, each running `turbo run <task>`.
  - Turbo tasks:
    - `build` (dependsOn `^build`, outputs `dist/**`)
    - `test`, `lint`, `typecheck`
    - `verify` (dependsOn `build`)
    - `e2e` (dependsOn `build`)
    - `deploy` (dependsOn `verify`, `cache: false`)
    - `preview` (dependsOn `verify`, `cache: false`)
  - `@gm/config/tsconfig.base.json`.

- [ ] **Step 1: Rename the repo and switch to `main`.**

```bash
gh repo rename websites -R GarrettManley/websites-garrettmanley.com --yes
cd /c/Users/Garre/Workspace/garrettmanley.com
git remote set-url origin git@github.com:GarrettManley/websites.git
git switch -c main && git push -u origin main
gh repo edit GarrettManley/websites --default-branch main
```

Then move the directory: `mv /c/Users/Garre/Workspace/garrettmanley.com /c/Users/Garre/Workspace/websites`. Expected: `git -C /c/Users/Garre/Workspace/websites status` is clean on `main`.

- [ ] **Step 2: Delete the legacy files** listed above.

- [ ] **Step 3: Write the root config.**
  - `package.json`:
    - `"private": true`
    - `"packageManager": "pnpm@12.18.0"`
    - `"engines": {"node": ">=24"}`
    - devDeps `turbo`, `@biomejs/biome`, `typescript`
  - `pnpm-workspace.yaml`: `packages: ["apps/*", "packages/*"]`
  - `.gitignore`: `node_modules/`, `dist/`, `.astro/`, `.turbo/`, `.wrangler/`, `test-results/`, `playwright-report/`
  - `.nvmrc`: `24`
  - `biome.json`:
    - formatter: 2-space indent, line width 100
    - linter: recommended
    - ignore `dist`, `.astro`
  - `tsconfig.base.json`:
    - `strict`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`
    - `module: "ESNext"`, `moduleResolution: "Bundler"`, `target: "ES2023"`

- [ ] **Step 4: Rewrite `README.md`.** Cover the purpose, the ring layout (copy the spec's Architecture tree), `pnpm i && pnpm verify`, and how to add an app.

- [ ] **Step 5: Add the project root to `~/AGENTS.md`.** Under Active project roots → Workspace, add:

```
- **`Workspace/websites/`** — personal web platform monorepo (`GarrettManley/websites`, public): Astro apps per domain (garrettmanley.com now; .dev lab, g.recipes, garrettmanley.app later) over shared `packages/{core,ui,tools}`. Spec: `docs/superpowers/specs/2026-11-10-web-platform-design.md`. Public repo: privacy gate `scrub-check` is mandatory.
```

- [ ] **Step 6: Verify.** Run `corepack enable && pnpm i && pnpm lint`. Expected: exit 0. Turbo reports no tasks to run yet, or Biome passes.

- [ ] **Step 7: Commit and push.** `chore: reset repo as websites monorepo (#1)`.

---

### Task 2: `packages/core` — domain schemas and rules

**Files:**
- Create:
  - `packages/core/package.json` (name `@gm/core`; deps `zod@^4.6.7`; devDeps `vitest`)
  - `packages/core/tsconfig.json`
  - `packages/core/src/domain/resume.ts`
  - `packages/core/src/domain/project.ts`
  - `packages/core/src/domain/post.ts`
  - `packages/core/src/domain/site.ts`
  - `packages/core/src/domain/slug.ts`
  - `packages/core/src/index.ts`
- Test:
  - `packages/core/tests/unit/resume.test.ts`
  - `packages/core/tests/unit/post.test.ts`
  - `packages/core/tests/unit/slug.test.ts`
  - `packages/core/tests/fixtures/public-resume.json` (synthetic data, no real PII)

**Interfaces:**
- Produces (all exported from `@gm/core`):
  - `PublicResume: z.ZodType` and `type PublicResume = z.infer<typeof PublicResume>`. Every object is `.strict()`. The shape mirrors career-ops `public_data()` (Task 3):
    - `basics{name, headline, location, email, url, linkedin, url_label, linkedin_label}` — no `phone`, no `address`; `email` must equal `"garrett@garrettmanley.com"` (`z.literal`)
    - `summary: string`
    - `skills: {category: string, items: string[]}[]`
    - `work: {company, location, roles: {title, period, intro: string|null, highlights: {id, text}[]}[]}[]`
    - `publications: {title, venue, date}[]`
    - `education: {school, degree, date}[]`
    - `certifications: {name, note}[]`
  - `Project` schema and type: `{id: string, name: string, summary: string, url: z.url(), tags: string[], featured: boolean}`.
  - `PostFrontmatter` schema and type: `{title: string, date: z.coerce.date(), summary?: string, tags: string[] (default [])}`.
  - `type PostSummary = {slug: string, title: string, date: Date, summary?: string}`.
  - `orderPosts(posts: PostSummary[]): PostSummary[]`: date descending, with ties broken by title ascending. The input is not mutated.
  - `type SiteLink = {label: string, href: string}` and `SiteLink` schema.
  - `slugify(title: string): string`: lowercase ASCII, with non-alphanumeric runs replaced by `-` and leading/trailing `-` trimmed.

- [ ] **Step 1: Write the failing tests.**
  - `resume.test.ts`:
    - `accepts the public fixture`
    - `rejects a phone field`: add `basics.phone` and expect `safeParse` to fail, with an issue code of `unrecognized_keys`
    - `rejects an address field`
    - `rejects any email other than garrett@garrettmanley.com`
    - `rejects extra keys on nested work roles`
  - `post.test.ts`:
    - `orderPosts sorts newest first`
    - `orderPosts breaks date ties by title`
    - `orderPosts does not mutate input`
    - `PostFrontmatter coerces ISO date strings`
  - `slug.test.ts`:
    - `"Advanced Merge Conflict Resolution"` → `"advanced-merge-conflict-resolution"`
    - `"C# & .NET: Tips!"` → `"c-net-tips"`
    - `"  --Hello--  "` → `"hello"`
- [ ] **Step 2: Run them and confirm they fail.** Run `pnpm --filter @gm/core test`. Expected: FAIL (modules missing).
- [ ] **Step 3: Implement the schemas and functions** above.
- [ ] **Step 4: Run them and confirm they pass.** Run `pnpm --filter @gm/core test && pnpm typecheck`. Expected: PASS.
- [ ] **Step 5: Commit.** `feat(core): domain schemas for resume, projects, posts (#1)`.

---

### Task 3: career-ops `--public` build (Career repo, private)

Read `C:\Users\Garre\Workspace\Career\CLAUDE.md` first and follow its conventions.

**Files:**
- Modify:
  - `Career/resume/build.py`: add `public_data()` and the `--public` flag in `main()`
  - `Career/resume/templates/ats.typ:24` and `styled.typ:33`: render the phone only when it is non-empty
  - `Career/resume/templates/resume.md.jinja:5-6`: address and phone lines become conditional
- Test: `Career/tests/test_resume.py`

**Interfaces:**
- Produces:
  - `public_data(data: dict) -> dict` returns a copy where:
    - `basics` drops `phone` and `address`
    - `basics.email = "garrett@garrettmanley.com"`
    - every highlight is reduced to `{id, text}` (drop `segments`)
  - `uv run resume/build.py --public` writes `resume/dist/public/` containing:
    - `Garrett_Manley_Resume_ATS.pdf`
    - `Garrett_Manley_Resume_Styled.pdf`
    - `resume.json` (`json.dumps(public_data(data), ensure_ascii=False, indent=2)`)
    - `ATS_parsed.txt`
  - PDFs are rendered from `public_data`, with `segments` kept for rendering. Concretely, render from `data` after removing the phone and address and setting the email, then write the JSON from `public_data`.

- [ ] **Step 1: Write the failing tests.**
  - `test_public_data_strips_phone_and_address(master)`: `"phone"` and `"address"` are absent from `public_data(build_data(master, None, False))["basics"]`.
  - `test_public_data_rewrites_email(master)`: the email is `"garrett@garrettmanley.com"`.
  - `test_public_data_highlights_are_id_text_only(master)`: every highlight's keys are `{"id", "text"}`.
  - `test_e2e_public_build_has_no_phone(tmp_path, master)`: model it on `test_e2e_ats_fidelity`. Build with public basics, then assert `master["basics"]["phone"]` and the first segment of `address` are both absent from the extracted ATS text. Also assert that no `\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}` match exists.
- [ ] **Step 2: Run them and confirm they fail.** Run `uv run --with pytest --with pyyaml --with typst --with jinja2 --with python-docx --with pdfplumber pytest tests/test_resume.py -q`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement** `public_data`, the conditional template fields and the `--public` flag.
- [ ] **Step 4: Run the tests again and confirm the whole file passes** (no regressions in the existing tests).
- [ ] **Step 5: Build.** Run `uv run resume/build.py --public`. Expected: `built ... -> resume/dist/public`, and the ATS fidelity check prints `OK`.
- [ ] **Step 6: Commit in the Career repo.** `feat(resume): --public build without phone/address for the website`.

---

### Task 4: `sync-resume` tool

**Files:**
- Create:
  - `packages/tools/package.json` (name `@gm/tools`; deps `@gm/core`, `yaml`, `node-html-parser`; script `build: tsc -p .` emitting `dist/`; `bin`: `scrub-check` → `dist/cli/scrub-check.js`, `sync-resume` → `dist/cli/sync-resume.js`, `import-ngblog` → `dist/cli/import-ngblog.js`, each with a `#!/usr/bin/env node` shebang)
  - `packages/tools/tsconfig.json`
  - `packages/tools/src/app/sync-resume.ts`
  - `packages/tools/src/adapters/fs-resume.ts`
  - `packages/tools/src/cli/sync-resume.ts`
- Test:
  - `packages/tools/tests/unit/sync-resume.test.ts`
  - `packages/tools/tests/integration/fs-resume.test.ts`
- Output (committed):
  - `content/shared/resume.json`
  - `apps/garrettmanley-com/public/resume/Garrett_Manley_Resume_{ATS,Styled}.pdf`

  The PDF destination's parent directory is created here, before Task 7 scaffolds the app. That is fine.

**Interfaces:**
- Consumes: `PublicResume` (Task 2). `Career/resume/dist/public/` (Task 3).
- Produces:
  - Ports, earned because both are filesystem IO:
    - `type ResumeReader = () => Promise<{json: unknown, pdfs: {name: string, bytes: Uint8Array}[]}>`
    - `type ResumeWriter = (resume: PublicResume, pdfs: {name: string, bytes: Uint8Array}[]) => Promise<void>`
  - `syncPublicResume(read: ResumeReader, write: ResumeWriter): Promise<PublicResume>`: it parses with `PublicResume.parse`, which throws a `ZodError` on violation, then writes.
  - `fsResumeReader(sourceDir: string): ResumeReader`: reads `resume.json` and the two PDFs by exact name. It throws if a PDF is missing.
  - `fsResumeWriter(contentDir: string, pdfDir: string): ResumeWriter`: writes pretty JSON (2-space indent, trailing `\n`).
  - CLI usage: `sync-resume --from <Career/resume/dist/public> --content <repo>/content/shared --pdf <repo>/apps/garrettmanley-com/public/resume`.

- [ ] **Step 1: Write the failing tests.**
  - Unit:
    - `passes a valid resume through to the writer` (in-memory ports, Task 2 fixture)
    - `throws and writes nothing when json has a phone field` (the writer spy is never called)
  - Integration:
    - `fsResumeReader + fsResumeWriter round-trip`: in a tmp dir with the fixture JSON and two dummy PDFs, the written JSON deep-equals the input and the PDF bytes are identical.
    - `fsResumeReader throws when a PDF is missing`
- [ ] **Step 2: Run them and confirm they fail.** Run `pnpm --filter @gm/tools test`.
- [ ] **Step 3: Implement** the app module, the adapters and the CLI. The CLI parses arguments with `node:util` `parseArgs` and wires the adapters into `syncPublicResume`.
- [ ] **Step 4: Run them and confirm they pass.**
- [ ] **Step 5: Run the real sync.** Run `pnpm --filter @gm/tools exec sync-resume --from ../../../Career/resume/dist/public --content ../../content/shared --pdf ../../apps/garrettmanley-com/public/resume`. Expected: exit 0, and `git diff --stat` shows the three files. Garrett eyeballs `content/shared/resume.json` before it is committed.
- [ ] **Step 6: Commit.** `feat(tools): sync-resume from career-ops public build (#1)`.

---

### Task 5: `scrub-check` privacy gate and `import-ngblog`

These two tools share the tools package's arg-parsing and file-walking patterns. They are split into two commits.

**Files:**
- Create:
  - `packages/tools/src/domain/scrub.ts`
  - `packages/tools/src/cli/scrub-check.ts`
  - `packages/tools/denylist.json`
  - `packages/tools/src/domain/ngblog.ts`
  - `packages/tools/src/adapters/gh-ngblog.ts`
  - `packages/tools/src/cli/import-ngblog.ts`
- Test:
  - `packages/tools/tests/unit/scrub.test.ts`
  - `packages/tools/tests/integration/scrub-cli.test.ts`
  - `packages/tools/tests/unit/ngblog.test.ts`
  - `packages/tools/tests/integration/gh-ngblog.test.ts`
  - `packages/tools/tests/fixtures/ngblog-export.json`: a copy of the public export, already fetched to the session scratchpad at `C:\Users\Garre\AppData\Local\Temp\claude\3b9d12fcbfaf7596\8359663c-f5df-48b6-8518-5f8c1418a2d0\scratchpad\ngblog\export.json`. Refetch it with `gh api repos/GarrettManley/ng-blog/contents/backups/garrettmanley-website-blogs-export.json -H "Accept: application/vnd.github.raw"`.
- Output (committed): `content/blog/*.md` (3 posts, after Garrett's review)

**Interfaces:**
- Scrub:
  - `type Rule = {id: string, pattern: string, flags: string, scope: "raw" | "text"}`
  - `type Hit = {file: string, rule: string, match: string}`
  - `scanContent(file: string, content: string, rules: Rule[]): Hit[]`: `raw` rules run on the full content. `text` rules run on HTML visible text (`node-html-parser`, with `script`/`style` removed) for `.html` files, and on the raw content otherwise.
  - CLI `scrub-check <distDir> [--rules <path>]`:
    - walks `.html .xml .txt .json .js .css .md`
    - skips any file named `denylist.json`
    - prints `file: [rule] match` per hit
    - exits 1 if there are any hits, otherwise 0
    - the default rules path is the package's `denylist.json`
- `denylist.json` rules (exact):
  - `private-repo-url` (raw, `i`): `github\.com/GarrettManley/(PRIVATE_NAMES)\b`. `PRIVATE_NAMES` is the `|`-joined output of `gh repo list GarrettManley --visibility private --limit 200 --json name -q '.[].name'`, generated once at implementation time and committed. The repo names themselves are not secret, but only private ones are listed.
  - `private-repo-slug` (text, `i`): `\baether-engine\b`
  - `local-path-win` (raw, `i`): `[a-z]:\\{1,2}users\\{1,2}`
  - `local-path-posix` (raw): `(?<![\w.])/(Users|c/Users)/[A-Za-z]`
  - `corporate-dir` (raw, `i`): `workspace[\\/]+duracell|\bmalachite\b`
  - `tracker-beads` (text): `\bhb-[a-z0-9]{3}(?:\.\d+)?\b`
  - `tracker-issue` (text): `(?<![\w&#/])#\d{2,5}\b`
- ng-blog:
  - `type NgBlogPost = {author: string, content: string[], postDate: string, postID: string}`, validated by a Zod schema in `ngblog.ts` (boundary validation)
  - `mapNgBlogPost(raw: NgBlogPost): {slug: string, markdown: string}`:
    - title = the first `content` line with its leading `# ` removed
    - body = the remaining lines joined with `\n`, trimmed
    - date = `postDate.slice(0, 10)`
    - slug = `slugify(title)`
    - markdown = YAML frontmatter `{title, date, tags: []}` via `yaml.stringify`, then a blank line, then the body
  - `ghNgBlogReader(): Promise<Record<string, NgBlogPost>>`: shells out to `gh api` (network IO). Tests use a file-reader variant over the fixture, which counts as the second implementation, earned at IO.
  - CLI `import-ngblog --out <repo>/content/blog [--from-file <path>]`

- [ ] **Step 1: Write the failing scrub tests (unit).** One test per rule that hits:
  - `flags a private repo URL` (use a name from the generated list)
  - `flags aether-engine`
  - `flags C:\\Users\\ path`
  - `flags /Users/ path`
  - `flags Workspace/Duracell`
  - `flags hb-28u.8`
  - `flags #139 in prose`

  Plus tests that pass:
  - `allows Duracell and Aether in prose`
  - `ignores hex colors and anchors`: `<style>a{color:#ff0000}</style><a href="#top">x</a>` produces no hits
  - `allows the public claude-marketplace URL`
- [ ] **Step 2: Write the failing scrub integration test.** `scrub-check exits 1 and names the file`: a tmp dist with `index.html` (clean) and `leak.html` (contains `C:\Users\x`) gives exit code 1, and stdout contains `leak.html` but not `index.html`. Then `exits 0 on a clean dist`.
- [ ] **Step 3: Run the tests and confirm they fail.** Then implement, then run them and confirm they pass. Generate `PRIVATE_NAMES` into `denylist.json`.
- [ ] **Step 4: Commit.** `feat(tools): scrub-check privacy gate (#1)`.
- [ ] **Step 5: Write the failing ng-blog tests.**
  - Unit:
    - `maps title from leading heading`
    - `preserves post date as YYYY-MM-DD`: `2019-08-16T15:22:39.079Z` → `date: 2019-08-16`
    - `escapes YAML-significant characters in title`: the title `Merge: "ours" vs theirs` round-trips through `yaml.parse` to the identical string
    - `rejects a post missing content`
  - Integration: `file reader over the fixture yields 3 posts`
- [ ] **Step 6: Run them and confirm they fail.** Implement, then run them and confirm they pass.
- [ ] **Step 7: Import the posts.** Run `import-ngblog --out ../../content/blog`. Expected: 3 `.md` files. **Garrett reviews each post** and deletes any stale one before the commit. Each kept post then passes `scrub-check content/blog`.
- [ ] **Step 8: Commit.** `feat(tools): import 2019 ng-blog posts (#1)`.

---

### Task 6: `packages/ui` — tokens, layout, components

**Files:**
- Create:
  - `packages/ui/package.json` (name `@gm/ui`; `exports` the `.astro` files and `./styles.css`; peer `astro`; dep `@gm/core` types-only)
  - `packages/ui/src/styles.css`
  - `packages/ui/src/tokens/tokens.css`
  - `packages/ui/src/layouts/BaseLayout.astro`
  - `packages/ui/src/components/SiteHeader.astro`
  - `packages/ui/src/components/SiteFooter.astro`
  - `packages/ui/src/components/ResumeView.astro`
  - `packages/ui/src/components/ProjectCard.astro`
  - `packages/ui/src/components/PostList.astro`

**Interfaces:**
- Consumes: `PublicResume`, `Project`, `PostSummary`, `SiteLink` (Task 2), as `import type` only.
- Produces (component props):
  - `BaseLayout{title: string, description: string, nav: SiteLink[], footerLinks: SiteLink[]}` with a default slot
  - `ResumeView{resume: PublicResume, pdfs: SiteLink[]}`
  - `ProjectCard{project: Project}`
  - `PostList{posts: PostSummary[], basePath: string}`
- Tokens:
  - `tokens.css` defines CSS variables on `:root`: `--color-bg`, `--color-fg`, `--color-muted`, `--color-accent`, `--color-surface`, `--font-sans`, `--font-mono`, `--radius`, `--space-*`.
  - Dark values go under `@media (prefers-color-scheme: dark)`.
  - `styles.css` holds `@import "tailwindcss"` plus an `@theme inline` block that maps Tailwind colors and fonts to those variables. Apps override only the variables, in their `theme.css`.

**Constraints:**
- Components contain no data access, no `fetch`, no `import.meta.glob`, and no `set:html` on data.
- The markup is semantic: `header`, `nav`, `main`, `article`, `footer`. There is a skip link, and every link is keyboard-focusable with a visible focus ring.
- No unit tests: these components have no conditional logic beyond rendering (Workspace testing rule). They are exercised by the Task 7 e2e and by `astro check`.

- [ ] **Step 1: Write tokens, styles and components** to the props above.
- [ ] **Step 2: Typecheck.** Run `pnpm typecheck`. Expected: PASS. Full verification happens in Task 7.
- [ ] **Step 3: Commit.** `feat(ui): design tokens and base components (#1)`.

---

### Task 7: `apps/garrettmanley-com`

**Files:**
- Create:
  - `apps/garrettmanley-com/package.json` (name `garrettmanley-com`; scripts below)
  - `apps/garrettmanley-com/astro.config.mjs`
  - `apps/garrettmanley-com/wrangler.jsonc`
  - `apps/garrettmanley-com/tsconfig.json`
  - `apps/garrettmanley-com/src/content.config.ts`
  - `apps/garrettmanley-com/src/data/{resume,projects,posts,site}.ts`
  - `apps/garrettmanley-com/src/styles/theme.css`
  - pages: `src/pages/{index,resume,projects,contact,404}.astro`, `src/pages/blog/index.astro`, `src/pages/blog/[slug].astro`
  - `content/shared/projects.json` (repo root)
  - `apps/garrettmanley-com/playwright.config.ts`
- Test: `apps/garrettmanley-com/tests/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: `@gm/core` (schemas and `orderPosts`), `@gm/ui` (components), `@gm/tools` (`scrub-check` bin), `content/`.
- Produces:
  - Package scripts:
    - `build`: `astro check && astro build`
    - `verify`: `scrub-check dist`
    - `e2e`: `playwright test`
    - `deploy`: `wrangler deploy`
    - `preview`: `wrangler versions upload --preview-alias pr-$PR_NUMBER`
- Config:
  - `astro.config.mjs`:
    - `site: "https://garrettmanley.com"`
    - `output: "static"`
    - integrations `[sitemap()]`
    - `vite.plugins: [tailwindcss()]`
  - `wrangler.jsonc`:
    - `name: "garrettmanley-com"`
    - `compatibility_date: "2026-11-01"`
    - `assets: {directory: "./dist", not_found_handling: "404-page"}`
    - `preview_urls: true`
    - `workers_dev: true`
    - **No `routes` yet.** Task 9 adds the custom domains.
  - `content.config.ts`:
    - `blog` = `glob({pattern: "**/*.md", base: "../../content/blog"})`, with schema `PostFrontmatter`
    - `projects` = `file("../../content/shared/projects.json")`, with schema `Project`
  - `src/data/resume.ts`: imports `../../../../content/shared/resume.json` and exports `PublicResume.parse(raw)`. This is boundary validation at build time.
  - `src/data/posts.ts`: maps collection entries to `PostSummary[]` and applies `orderPosts`. Components never see `CollectionEntry`.
  - `src/data/site.ts`:
    - `nav`: Home `/`, Resume `/resume/`, Projects `/projects/`, Blog `/blog/`, Contact `/contact/`
    - `footerLinks`: GitHub `https://github.com/GarrettManley`, LinkedIn (`resume.basics.linkedin`), Lab `https://garrettmanley.dev`, Bluesky (the profile URL is confirmed with Garrett at Step 4)
- `projects.json` entries `{id, name, summary, url, tags, featured}`:
  - `lab` → `https://garrettmanley.dev`
  - `aether` → `https://garrettmanley.dev/aether/`
  - `claude-marketplace` → `https://github.com/GarrettManley/claude-marketplace`
  - Each other candidate must pass `gh repo view GarrettManley/<name> --json visibility -q .visibility` = `PUBLIC` before it is listed.
- Page content:
  - home: a short about drafted from `resume.summary`, 3 featured projects and the 3 latest posts
  - resume: `ResumeView` plus the PDF links `/resume/Garrett_Manley_Resume_ATS.pdf` and `/resume/Garrett_Manley_Resume_Styled.pdf`
  - contact: `garrett@garrettmanley.com` plus the footer links

- [ ] **Step 1: Write the failing e2e test** in `smoke.spec.ts`. The Playwright `webServer` is `pnpm astro preview --port 4321`.
  - `core routes return 200`: `/`, `/resume/`, `/projects/`, `/blog/`, `/contact/`, and the first post's URL.
  - `nav links resolve`: click every nav link, and none lands on the 404 page.
  - `unknown route is 404`: `/does-not-exist` returns status 404 with the 404 page heading. Run this against `wrangler dev` (in its own `test.describe`, with a second `webServer` entry `pnpm wrangler dev --port 8787`), because `astro preview` does not apply `not_found_handling`.
  - `resume renders literal ampersand`: if any resume text contains `&`, its rendered text contains `&` and not `&amp;`. Select the text via `getByText`.
  - `resume pdf links resolve`: GET both PDF URLs, status 200 and `content-type` `application/pdf`.
- [ ] **Step 2: Run it and confirm it fails.** Run `pnpm build && pnpm --filter garrettmanley-com e2e`. Expected: FAIL (the pages don't exist yet).
- [ ] **Step 3: Implement** the config, data mappers, theme and pages. **Garrett reviews the drafted about, project and contact copy before the commit.**
- [ ] **Step 4: Run the full pipeline.** Run `pnpm verify && pnpm --filter garrettmanley-com e2e`. Expected: `astro check` reports 0 errors, the build succeeds, `scrub-check` exits 0, and the e2e passes. Then run `lychee --offline --root-dir apps/garrettmanley-com/dist apps/garrettmanley-com/dist`. Expected: 0 errors.
- [ ] **Step 5: Run the gate proof.** Temporarily add `C:\Users\test` to `contact.astro`, run `pnpm verify`, and expect exit 1 naming `contact/index.html`. Revert. Then temporarily add `"phone": "x"` to `content/shared/resume.json`, run `pnpm build`, and expect it to fail with `unrecognized_keys`. Revert.
- [ ] **Step 6: Commit.** `feat(com): garrettmanley.com app (#1)`.

---

### Task 8: CI/CD and dependency updates

**Files:**
- Create:
  - `.github/workflows/ci.yml`
  - `.github/dependabot.yml`

**Interfaces:**
- Consumes: the root scripts (Task 1) and the app's `deploy`/`preview` scripts (Task 7).
- Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

`ci.yml` triggers on `pull_request` and on `push` to `main`. It has one job on `ubuntu-latest`. Steps:
1. Check out with `fetch-depth: 0`.
2. Set up pnpm and Node with `node-version-file: .nvmrc` and `cache: pnpm`.
3. Run `pnpm i --frozen-lockfile`.
4. Run `pnpm turbo run lint typecheck test verify --affected`.
5. Run `pnpm exec playwright install --with-deps chromium && pnpm turbo run e2e --affected`.
6. Run `lycheeverse/lychee-action@v2` with `args: --offline --root-dir ... apps/*/dist`, `fail: true`.
7. On PRs: run `pnpm turbo run preview --affected` with env `PR_NUMBER`, then post a sticky comment with `gh pr comment` linking `https://pr-<n>-garrettmanley-com.<account-subdomain>.workers.dev`. Read the subdomain from the `wrangler versions upload` output.
8. On `main`: run `pnpm turbo run deploy --affected`.

Turbo `--affected` compares against `main`, so one app's change only deploys that app (the spec's acceptance criterion). Before step 4, the workflow skips cleanly if the secrets are absent (fork PRs).

`dependabot.yml`: weekly updates for `npm` (one grouped PR for minor/patch) and `github-actions`.

- [ ] **Step 1: Create the API token.** Garrett confirms each click while it is created in the Cloudflare dashboard via Claude in Chrome. It uses the "Edit Cloudflare Workers" template, restricted to this account and to the garrettmanley.com zone (the zone is needed for Task 9 custom domains). Then run `gh secret set CLOUDFLARE_API_TOKEN -R GarrettManley/websites` and do the same for `CLOUDFLARE_ACCOUNT_ID`.
- [ ] **Step 2: Write the two files.**
- [ ] **Step 3: Verify on a branch.** Open a PR from `ci/setup`. Expected: CI is green, and a PR comment carries a preview URL that serves the site.
- [ ] **Step 4: Prove the gate fails CI.** On a throwaway PR, add `hb-abc` to a blog post. Expected: the CI `verify` step fails. Close that PR unmerged.
- [ ] **Step 5: Merge the CI PR.** Expected: the `main` run deploys, and `https://garrettmanley-com.<subdomain>.workers.dev` serves the site.

---

### Task 9: DNS cutover for garrettmanley.com

Operations work through Claude in Chrome on the Cloudflare dashboard. Garrett confirms each destructive click. Before starting, screenshot the zone's DNS records and Rules list into the migration doc as the rollback reference.

**Files:**
- Modify:
  - `apps/garrettmanley-com/wrangler.jsonc`: add `routes: [{pattern: "garrettmanley.com", custom_domain: true}, {pattern: "www.garrettmanley.com", custom_domain: true}]`
  - `Workspace/docs/migrations/2026-11-10-squarespace-to-cloudflare.md`: update the `.com` section

- [ ] **Step 1: Garrett signs off** on the `workers.dev` deploy after reviewing it.
- [ ] **Step 2: Delete the conflicting records** in the garrettmanley.com zone (Cloudflare dashboard):
  - apex A `198.185.159.144` and `198.185.159.145`, if present
  - `www` CNAME `ext-sq.squarespace.com`
  - `_domainconnect` CNAME
  - the redirect rule sending the apex/www to `github.com/GarrettManley`

  **Do not touch** MX, SPF TXT, `_dmarc` or `_atproto`.
- [ ] **Step 3: Merge the custom domains.** Merge a PR adding the `routes` above. CI deploys, and Cloudflare creates the DNS records and certificates. Expected: Workers → garrettmanley-com → Domains lists both hosts as Active.
- [ ] **Step 4: Redirect www to the apex.** Create a Single Redirect rule: when hostname = `www.garrettmanley.com`, dynamic redirect `concat("https://garrettmanley.com", http.request.uri.path)`, status 301, preserve query string.
- [ ] **Step 5: Verify:**
  - `curl -sIL https://garrettmanley.com` gives `HTTP/2 200`, `server: cloudflare`, and no `location: https://github.com`.
  - `curl -sI "https://www.garrettmanley.com/blog/?y=1"` gives `301` with `location: https://garrettmanley.com/blog/?y=1`.
  - `nslookup -type=MX garrettmanley.com 1.1.1.1` is unchanged from the migration doc.
  - Garrett sends a test email to `garrett@garrettmanley.com`, and it arrives in Gmail.
  - Lighthouse (Chrome DevTools via Claude in Chrome) scores ≥ 95 on performance, accessibility and SEO.
- [ ] **Step 6: Update the migration doc and the issue.** Update the doc's `.com` section, records and open items. Commit it in Workspace with `WORKSPACE_SKIP_PUBLISH=1`, after `_scripts/pre_commit_audit.ps1` and `verify_workspace.ps1` pass. Tick Phase 1 on issue #1.
- [ ] **Step 7: Run the architecture review.** Run `review:architecture-conformance` over `git diff <Task-1-base>..main` in the websites repo. Expected: 0 dependency-direction or earned-abstraction findings. Fix any findings before closing Phase 1.

---

## Out of scope here (later plans)

- **Phase 1b:** lab on Cloudflare (`publish.ps1` swap, lab scrub cleanup, `/hire/` stub, .dev cutover).
- **Phase 2:** the lab port.
- **Phase 3:** Firebase decommission and revoking the loose service-account key.
