# Retrospective: Project showcase on garrettmanley.com (mtga-companion first)

**Plan:** `~/.claude/plans/i-m-looking-to-put-rosy-lake.md`
**Commit:** websites main `3eb2431` (`feat(com): project case studies, mtga-companion first`), then `0ba8b97` (`feat(com): Open Graph tags for link previews`); Workspace `8b85caa` (spec and plan)
**Date:** 2026-11-20

## Outcome

garrettmanley.com has a case-study page type, and `/projects/mtga-companion/` is the first page:
- Six hand-drawn architecture figures, each with an edge-by-edge key that is also its text equivalent.
- A 21-row stack table, five compact decision records, a script-free carousel of five overlay screenshots and one real tool response.
- About 475 words of body prose, down from about 1,340 in the first version.
- Ten new design-system components, a shared diagram vocabulary and a diagram lint in the websites repo.
- Open Graph tags on every page.
- The design-system book mirrors the repo again: eleven component cards, the diagram rules and the token change.

The second case study needs a content file and its diagrams.

## What worked

- **Evidence pack before prose.** Every number and every "rejected alternative" was read at the source and written into a private evidence pack first. The first sketch of the four headline numbers was wrong three times once verified.
- **Draw, measure, critique, fix.** A small harness rendered each figure with the real fonts and reported overlaps, clipped labels and edges through text. Figures converged in two or three rounds without a person looking at each one.
- **Adversarial claim checks after every rewrite.** A review of the rebuilt page against the source corrected 44 statements, one of them a claim about who ran the production migrations.
- **Workflow resume.** The machine restarted mid-workflow. Resuming from the run id reused 26 finished agent results.
- **Independent review before anything public.** A separate agent read the first screenshots and the carousel before the first public push and found six real defects and no privacy problem.
- **Staging states through files.** The overlay's collapsed and hidden states live in its layout file, so each screenshot state was staged by writing that file. No key press or click was simulated on the desktop.
- **Checking where a commit goes before making it.** The spec was headed for a public repo with a publish hook. Checking visibility first led to stripping the private sources.

## Friction / bugs

- **The first version was a write-up, not a showcase**
  - *What happened:* Version 1 shipped to preview with one diagram, a row of tags and long decision narratives. The owner asked for more stack detail and more architecture diagrams.
  - *Root cause:* The design was approved as an outline. Nobody saw the page's shape until it was built.
  - *How caught:* Owner review of the preview.
  - *Fix:* Rebuilt around a stack table and six views; the long narratives were kept privately.
  - *Rule:* For a page people will look at, show a sketch of the page before writing its content. An approved outline is not an approved layout.

- **A class-list typo passed every gate**
  - *What happened:* A missing space in a Tailwind class list dropped the figure frame's padding and centring. Build, lint, type check, unit tests and e2e all passed.
  - *Root cause:* Tailwind ignores a class it cannot parse, and no test looked at pixels.
  - *How caught:* Reading a screenshot.
  - *Fix:* Restored the space.
  - *Rule:* For a UI change, a screenshot at phone and desktop width is part of the gate.

- **The capture helper swallowed its own failure**
  - *What happened:* The first two screenshot runs exited 0 and saved nothing.
  - *Root cause:* The helper caught only one exception type and ignored it; the screen-copy call threw a different one.
  - *How caught:* The output folder was empty.
  - *Fix:* The helper logs every exception to a file, and the copy uses a direct blit that includes layered windows.
  - *Rule:* A helper that produces an artifact reports when it produced nothing.

- **A capture run was stopped by the owner**
  - *What happened:* A run that opens windows on the desktop was started without saying so, and the owner stopped it.
  - *Root cause:* The earlier go-ahead was treated as covering later runs.
  - *How caught:* The owner killed the task.
  - *Fix:* Checked that nothing was left open, explained what the next runs would do, and waited.
  - *Rule:* Announce every run that puts a window on the user's screen, each time.

- **Requested states existed only on an unmerged branch**
  - *What happened:* The owner asked for collapsed and hidden boxes in the screenshots. Those features were only on the project's next sprint branch, while every other claim on the page was checked against main.
  - *Root cause:* The owner uses the newer build day to day; the page was pinned to main.
  - *How caught:* Reading the source before capturing.
  - *Fix:* Asked, then captured from the sprint branch with the owner's approval and recorded in the pull request that the screenshots are ahead of main.
  - *Rule:* When a request depends on unmerged work, say so before doing it, and record what must be re-checked after the merge.

- **First carousel: focus ring off-screen, page jump on click**
  - *What happened:* The hidden radio inputs sat at the top of the frame and the controls below the image, so focus could be invisible and a click could scroll the page.
  - *Root cause:* In the radio-and-label pattern the focused element is the hidden input, not the visible control.
  - *How caught:* Independent review, measured in a headless browser.
  - *Fix:* Controls moved above the image and the inputs pinned into that row; an e2e test asserts the page does not scroll.
  - *Rule:* In a script-free radio pattern, put the hidden inputs where the visible controls are.

- **A caption contradicted its own image**
  - *What happened:* A caption said card names are tinted by card colour. That is true in one box and false in another.
  - *Root cause:* The caption was written from a glance at the image.
  - *How caught:* Independent review; the rule was then read in the source.
  - *Fix:* Caption corrected, and later replaced.
  - *Rule:* A caption is a claim. Check it against the source, not the picture.

- **Worktree removal half-failed on Windows**
  - *What happened:* `git worktree remove` deleted the registration and failed on the folder. An editor's TypeScript server held files inside it.
  - *Root cause:* Open handles on `node_modules` from an editor that had indexed the worktree.
  - *How caught:* The command's error output.
  - *Fix:* Deleted the folders by hand. Three empty admin folders remain until the editor restarts.
  - *Rule:* Before removing a worktree, check for processes whose command line names it.

- **Handoff note written into a nested public repo**
  - *What happened:* The handoff script, run from inside a worktree, wrote its note into the nested repo's checkout.
  - *Root cause:* The script resolves its destination from the current directory.
  - *How caught:* Its own output line named the wrong path.
  - *Fix:* Re-ran from the workspace root and removed the stray file.
  - *Rule:* Run workspace-level scripts from the workspace root, and read the path they report.

- **A docs commit triggers a deploy that needs a person**
  - *What happened:* Committing the spec ran the publish chain. It waited for a Windows Hello approval, timed out, and left four generated files changed.
  - *Root cause:* The deploy step needs an interactive approval that an agent session cannot give, and the script does not clean up after a failure.
  - *How caught:* The commit output and `git status`.
  - *Fix:* Restored the generated files; the owner approved a later run.
  - *Rule:* Before committing under `docs/` here, tell the owner a prompt is coming.

## Concrete improvements

- **Diagram render-and-measure harness** — kept in the websites checkout's ignored workspace. Follow-up: move it into the websites tools package so the next case study has it by default.
- **Diagram lint in core** — keeps drawn labels and key labels identical; done.
- **Carousel guards** — a repeated id or mixed image sizes are not rejected; follow-up.
- **Caption re-check** — the five screenshot captions must be re-read when the project's next sprint merges; pending.
- **Preview image for shared links** — the Open Graph tags carry text only; follow-up.
- **Design-system book** — the site header and footer, the project card, the post list and the resume view are not mirrored yet; follow-up.
- **Publish chain** — it leaves generated files changed after a run; follow-up to restore or commit them inside the script.
- **Stripping private sources from public specs** — done for this spec and plan; recorded in project memory as the default for any spec that cites a private repo.
