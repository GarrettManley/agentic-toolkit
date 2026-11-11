# Retrospective: garrettmanley.com cutover, Firebase decommission, Dependabot triage

**Plan:** `~/.claude/plans/let-s-plan-out-our-prancy-ladybug.md`
**Commit:** `faf3115` (`chore: decommission Firebase tooling (lab moved to Cloudflare)`); websites main `6e026b8`
**Date:** 2026-11-11

## Outcome

garrettmanley.com now serves the Astro site from the `garrettmanley-com` Worker:
- Custom domains cover the apex and www.
- www redirects to the apex with a 301, keeping the query string.
- Always Use HTTPS is on.
- Mail works, confirmed with an external sender.
- Lighthouse on the live site: performance 99, accessibility 100, best practices 96, SEO 100.

Firebase hosting is decommissioned:
- The old lab site serves only a noindex redirect, so the public resume PDF with a phone number is gone.
- Four stale sites are disabled.
- Two GCP service accounts and their keys are deleted, along with the websites secret.
- The local CLI, plugins and extensions are removed.
- scrum-estimator intentionally stays on Firebase.

The scope widened at Garrett's request to remove openclaw as well (an npm global and a GCP service account).

Seven Dependabot PRs were resolved through two superseding PRs (#16, #17) plus ignore rules. Phase 1 of websites#1 is closed.

## What worked

- **Read-only snapshot before destructive steps.** Reading the CF zone first showed 0 Redirect Rules. That proved the GitHub redirect lived on the Squarespace origin, so the plan's "repoint the existing rule" step became "create a new rule" before anyone clicked anything.
- **Split by who acts.** The agent wrote exact delete lists. Garrett performed every DNS and service-account deletion, which the classifier blocks agents from doing. The agent did creates and toggles only when Garrett asked for them. This ran without friction.
- **Background inventory agent.** An Explore agent mapped Firebase and openclaw across the machine while the cutover ran. It found items the plan didn't know about: the root `firebase.json`, the misleading `firebase-standards.md` agent doc, the MCP whitelist entry, and the enabled Gemini extension.
- **Lighthouse as a real gate.** Measuring the live site and the preview exposed a Phase 1 bug: Tailwind never generated the @gm/ui utilities. The 94 accessibility score came from footer links with no layout classes applied.
- **Superseding PRs instead of waiting on Dependabot.** One branch per lockfile-overlap group gave one CI run against current main and no rebase churn.
- **Subagent quality.** Both the Explore inventory and the review:architecture-conformance agent produced clean, accurate output with no hallucinated findings. The conformance agent verified claims by `git grep` rather than by asserting them.

## Friction / bugs

- **Merged a red PR (websites#12)**
  - *What happened:* `gh pr checks 12 | head; gh pr ready 12 && gh pr merge 12 …` merged while CI was failing.
  - *Root cause:* `checks` was a display step. Nothing in the `&&` chain depended on its result.
  - *How caught:* the output, read right after the merge, showed `fail`.
  - *Fix:* the failure was a latent race between `astro check` and `astro build`, both rewriting `.astro/content-assets.mjs`, which made it intermittent. #13 made `typecheck` depend on `build`. The main deploy had passed anyway.
  - *Rule:* never put `gh pr merge` in a chain unless it gates on `gh pr checks --watch` (its exit status), or on a separate, explicit read of a green result.

- **Tailwind skipped the shared UI package since Phase 1**
  - *What happened:* the live CSS was 7.5 KB and lacked `min-h-screen`, `flex-wrap`, `gap-x-6` and similar classes. The footer and layout rendered unstyled.
  - *Root cause:* Tailwind v4 auto-detection starts at the app root and ignores workspace packages resolved through `node_modules`.
  - *How caught:* Lighthouse `target-size`. The bounding rects showed links touching with no gap, even though the markup had `gap-x-6`.
  - *Fix:* `@source "./";` in `packages/ui/src/styles.css`, placed after the `@import`s because biome rejects it otherwise. Shipped in #14.
  - *Rule:* in a Tailwind v4 monorepo, any package that emits class names needs an explicit `@source`. Assert one shared-package utility exists in the built CSS. That is cheap, and it belongs below the e2e level.

- **Plan assumed the wrong Firebase project and key**
  - *What happened:* the plan put `garrettmanley-lab` in project `garrettmanley` and treated the Downloads key as its deploy credential. The site was actually in `garrettmanley-website`. The key belonged to the unrelated `openclaw` service account. The websites secret was backed by a third key, from `github-action-947170143`.
  - *Root cause:* the spec was written from memory of the setup, never from `firebase hosting:sites:list`.
  - *How caught:* the read-only inventory step before deploying.
  - *Rule:* an existing instinct already covers this: read the actual resource before asserting how it is wired. For cloud resources, list them (sites, service accounts, keys) before a plan names them.

- **Dependabot ignored `@dependabot rebase`**
  - *What happened:* there was no rebase after more than 5 minutes.
  - *Fix:* applied the bumps on our own branches (#16, #17) and closed the originals as superseded.
  - *Rule:* do not wait on Dependabot. When PRs overlap on the lockfile or are behind main, supersede them.

- **Local toolchain gaps**
  - *What happened:* `pnpm` is not on PATH, so `turbo run` fails locally with "cannot find binary path". The `lighthouse` JSON output broke Python's default cp1252 read.
  - *Fix:* `corepack pnpm …` for install and tests, PR CI for turbo, and `open(..., encoding="utf-8")`.
  - *Rule:* already captured as instincts (cp1252) and in the handoff (corepack).

- **Force-added an untracked ledger**
  - *What happened:* `git add -f` committed the SDD `progress.md`. No other ledger is tracked.
  - *How caught:* checked `git ls-files .superpowers` right after the commit.
  - *Fix:* `git rm --cached` and amended the commit, which was still unpushed.
  - *Rule:* don't `-f` add a file whose siblings are untracked. Check the convention first.

## Concrete improvements

- **websites#15** — architecture minors: move the scrub file-selection rule into domain, add an ngblog app port, deduplicate fixtures. Pending.
- **Shared-UI CSS assertion** — a unit/integration check that the built CSS contains a @gm/ui-only utility, so `@source` cannot regress. Follow-up, not yet filed.
- **Merge gating habit** — recorded in the `.remember/remember.md` "don't retry" list. Done.
- **TS 7 revisit** — remove the dependabot `typescript` major ignore once Astro supports TS 7. Follow-up.
- **DMARC `p=reject`** — after the observation window. Pending (migration doc).
