# Retrospective: Web platform — .com cutover → Firebase decommission → Dependabot triage

**Plan:** `~/.claude/plans/let-s-plan-out-our-prancy-ladybug.md`
**Commit range:** `aa477cf..faf3115` (Workspace) + `websites#12`/`#14`/`#15`/`#16`/`#17` (websites)
**Date:** 2026-11-11

## Outcome

Three workstreams shipped in a single session: (A) `garrettmanley.com` cut over from Squarespace-proxied-A-records-redirecting-to-GitHub to a Cloudflare Workers custom-domain pair (`garrettmanley.com` + `www.garrettmanley.com` → 301 → apex). The live site serves the Astro .com app with Lighthouse 99/100/96/100 and the external-sender mail round-trip succeeded. (B) Firebase Hosting decommissioned — the old `garrettmanley-lab.web.app` now serves a `noindex` meta-refresh on every path (killing the resume-PDF privacy leak), 4 sibling sites have hosting disabled, the GitHub service-account secret + the GCP service accounts + the Downloads key file are all gone, and `firebase-tools` + `openclaw` are uninstalled locally. Scope widened mid-execution to audit Firebase + openclaw end-to-end. (C) Dependabot triage: 7 PRs closed — 2 rollup merges (#4/#5/#6 → #16; #9/#10 → #17) and 2 ignore rules (TypeScript major, @types/node major) that Dependabot auto-closed against. `main` CI green; 0 open PRs.

## What worked

- **Order-matters framing on workstream B.** "Deploy the redirect while the SA key still works, then revoke" was the plan rule. Executing in that order kept the PDF offline continuously; reversed, there would have been a window where the key was gone and `firebase deploy` couldn't push the fix.
- **Snapshot-before-delete on DNS.** Writing the current `.com` zone records into the migration doc before any destructive dashboard action turned "did we delete something load-bearing?" into a 3-second diff instead of a 30-minute panic. Kept the MX/DMARC/_atproto rows intact.
- **Explicit `Garrett clicks every destructive dashboard action`.** Classifier blocks agent DNS/rule deletes anyway; naming the convention up-front turned it from friction into a clear role-split with no handoff drops.
- **Single-redirect template over custom Worker.** The "WWW to root" dashboard template did exactly what the plan needed (301, query string preserved) with zero code — matched the "site stays assets-only" standing constraint.
- **Scope-widening with permission.** Workstream B grew from "disable Firebase on the one site" to "full Firebase + openclaw audit" after inventory surfaced sibling sites + a second service account. Done with explicit mid-session OK.

## Friction / bugs

- **websites#12 merged with red CI**
  - *What happened:* The .com custom-domain routes PR merged before `astro check`/`build` finished green. The CI job failed; the agent didn't notice.
  - *Root cause:* `gh pr merge` was chained after `gh pr checks` without inspecting the exit code — the checks command "succeeded" at reporting, not at being green.
  - *How caught:* Garrett noticed the red badge on main; follow-up fix in `websites#13`.
  - *Fix:* Every subsequent merge gated on an explicit `gh pr checks --watch` (or the equivalent green-state assertion) before `gh pr merge`.
  - *Rule:* Never chain merge after checks without asserting-green. The CI status check is a predicate, not a progress indicator — treat its exit code as a gate.

- **Lighthouse "best practices" scored 96 instead of 100**
  - *What happened:* Preview deploys score 100; the live site scores 96.
  - *Root cause:* The Cloudflare analytics beacon on the live domain — the test machine's DNS blocks the beacon host, which Lighthouse reads as a "failed network request" penalty.
  - *How caught:* Garrett ran Lighthouse on both hosts and compared.
  - *Fix:* Not fixed — documented in the Workstream A verification summary as the one deviation from the spec target.
  - *Rule:* Network-blocked analytics beacons penalize Lighthouse best-practices. When the live site sends a beacon the preview doesn't, expect the drift; plan accordingly.

- **Firebase project name assumption**
  - *What happened:* The plan claimed `garrettmanley-lab` lived in the `garrettmanley` GCP project. It actually lives in `garrettmanley-website`.
  - *Root cause:* Memory-sourced guess during plan authorship; not checked against `firebase projects:list` until Workstream B step 1 ran.
  - *How caught:* The inventory step immediately showed the real project.
  - *Fix:* Did the remaining B steps against `garrettmanley-website`; no fallout.
  - *Rule:* Project/account identifiers in a plan are claims, not facts. The first step of any decommission workstream is `list`, and it's cheap enough to always run.

## Concrete improvements

- **`.github/dependabot.yml` ignores** for `typescript` major and `@types/node` majors > 24 — websites repo, status **done**. Keeps Dependabot from refiling PRs that can't merge until the ecosystem (astro-check on TS 7) catches up or the runtime moves (Node major bump).
- **Migration doc updated** at Workspace `850d407` with `.com` + `.dev` sections, log rows, and retired validation items — status **done**.
- **`review:architecture-conformance` ran against `aa477cf..main`** on websites — 0 dependency-direction findings, 0 earned-abstraction findings; the minors land in `websites#15` — status **done**.
- **openclaw + firebase-tools uninstalled locally + Workspace config/docs cleaned** at `faf3115` — status **done**.
- **Garrett's remaining backlog** (named in the plan's "End of session" section, status **pending**, outside this retro's scope): `www.garrettmanley.dev`, blog follow-ups, Career `feat/public-resume-build` merge, registrar transfer (Phase 4, on hold), the ledger's deferred CI hardening items.

## Marker-placement note

The pending-retrospective marker for this plan landed in `C:/Users/Garre/Workspace/Roleplaying/retrospectives/pending/` even though the plan covers Workspace/websites work. That's the exit-plan-mode hook following cwd at plan-mode time, not plan content. Writing this retro in `Workspace/retrospectives/done/` (the correct workspace for the plan's actual deliverables) and clearing the Roleplaying marker as stale.
