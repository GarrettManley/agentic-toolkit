# Retrospective: Personal design system — "gm" (Circuit Night)

**Plan:** `~/.claude/plans/i-m-looking-to-create-squishy-graham.md`
**Commit:** websites `1f6a609` (`feat(ui): gm design system "Circuit Night" tokens, Plex fonts and brand mark (#18)`); follow-ups in websites PR #19
**Date:** 2026-11-12

## Outcome

garrettmanley.com now uses the gm "Circuit Night" design system:

- **Tokens:** a dark-first semantic token set with a `[data-theme]` light override, gated by a 51-case WCAG contrast unit test.
- **Fonts:** IBM Plex, self-hosted (no font CDN).
- **Brand mark:** a hand-traced SVG brand mark used in the header and the favicon.
- **PR #19:** adds a home-page headshot and a header mark that draws itself on load, and drops the redundant "Home" nav link.

A hosted Design System artifact documents the system and the three direction boards it was chosen from. Not built yet:

- the token export script (`build-tokens.mjs`)
- the Button, Tag, Prose and CodeBlock components
- the lab-site theme
- syncing the artifact from the repo

## What worked

- **Same specimen set on every direction board.** Garrett could compare A, B and C side by side, and the pick (A) took one round.
- **Seeding the directions from Garrett's own images.** Palettes sampled from his inspiration assets made the options feel personal rather than generic.
- **Measured logo tracing:** skeletonize the source, fit lines and arcs, render, then diff against the source.
  - Stroke IoU against the source raster (0.967 → 0.970) gave an objective "closer or worse?" signal for each geometry tweak.
- **Contrast checks as a unit test over `tokens.css`.** Theme changes now fail CI instead of relying on eyeballing.
- **Building the site, then checking it in the built-in browser** (dark, light, 375px, and the animation timeline sampled mid-draw). This caught layout issues that the build and the e2e tests can't.

## Friction / bugs

- **Logo "doesn't look right" on the first SVG rebuild**
  - *What happened:* The first rebuild of option #5 used a grid and was eyeballed. Garrett rejected it.
  - *Root cause:* I approximated the geometry from a downscaled preview instead of measuring the source raster.
  - *How caught:* Garrett's review.
  - *Fix:* Traced the full-resolution JPG with the skeleton/fit/diff pipeline.
  - *Rule:* When reproducing an existing raster mark, measure against the source (diff or IoU) from the start. Never freehand it.
- **Serif kink at the G terminal**
  - *What happened:* The fitted geometry left a small serif-like bump where the G's stroke ends.
  - *Root cause:* The end corners were fitted as free points instead of being constrained to the inner and outer bowl circles.
  - *How caught:* Garrett's review. IoU barely moved, because a sub-pixel bump is invisible to an area metric.
  - *Fix:* Made the terminal one straight leg with both ends on the bowl circles.
  - *Rule:* Area metrics miss tip and corner artifacts. Zoom-inspect the terminals as well as checking IoU.
- **ClipPath notch clipped the bar end**
  - *What happened:* The clip notch that cuts the M's free end was too wide.
  - *How caught:* Overlay render.
  - *Fix:* Narrowed the notch.
- **A stray `python -` hung waiting on stdin**
  - *What happened:* A heredoc-less `python -` call blocked the shell.
  - *Fix:* Stopped the task and made the edits with the Edit tool.
  - *Rule:* This is already in feedback memory ("never leave a heredoc open").
- **PR target mismatch**
  - *What happened:* The `create-pr` command defaulted to the Workspace repo (`agentic-toolkit`/`master`), but all of the changes live in the nested `websites` repo.
  - *Fix:* Opened the PR on `websites` and said so explicitly.
  - *Rule:* Resolve the PR repo from where the diff lives, not from the session cwd.

## Concrete improvements

- **Opt-in `draw` prop on `Mark.astro`.** Reduced-motion safe, and enabled on `/` only so the animation doesn't replay on every navigation. Done (websites PR #19).
- **`build-tokens.mjs` → `tokens.json` plus Mermaid theme variables.** Pending; it isn't needed until a second consumer exists (mtga-companion, scrum-estimator, or the artifact sync).
- **Lab-site (`garrettmanley.dev`) Circuit Night theme and a design-system section in the README.** Follow-up.
- **Lighthouse re-run on the live site** after the font and headshot changes, holding the 99/100/96/100 bar. Pending once PR #19 deploys.
