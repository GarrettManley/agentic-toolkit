# RCA: Disappearing `site/content/docs/toolkit/` files on commit

Trace ID: investigation-2026-05-07-publish-toolkit
Status: forensic-only (read-only, no fixes applied)

## 1. Pipeline trace

Post-commit hook fires unconditionally:

- `C:/Users/Garre/Workspace/.git/hooks/post-commit:5` invokes `powershell.exe -NoProfile -Command "C:\Users\Garre\Workspace\publish.ps1"`.

`publish.ps1` decides whether to skip:

- `publish.ps1:9-22` — skip-publish guard. Diffs `HEAD~1..HEAD`; if **every** changed path starts with `sec-research/`, exits 0. Otherwise falls through to the pipeline.
- `publish.ps1:28` — `uv run .ai/scripts/publish_toolkit.py`.
- `publish.ps1:32` — `uv run .ai/scripts/generate_spec.py`.
- `publish.ps1:37` — `uvx hugo`.
- `publish.ps1:42` — `npx firebase-tools deploy`.

`publish_toolkit.py` is destructive-then-rebuild:

- `.ai/scripts/publish_toolkit.py:58-59` — `if os.path.exists(TOOLKIT_OUTPUT): shutil.rmtree(TOOLKIT_OUTPUT)`. **This is the deletion source.**
- `.ai/scripts/publish_toolkit.py:61-62` — re-walks `.ai/skills/` and `.ai/scripts/` and rewrites every output file, wrapped in fresh Hugo frontmatter (`date:` set to `datetime.now()`).

`generate_spec.py` regenerates ADR docs (`001-…md`, `002-…md`, `003-…md`) at `.ai/scripts/generate_spec.py:68-70` — this is what re-stamps those three with today's date and is the source of the `M` entries on `001/002/003-*.md`.

## 2. Root cause

Two compounding faults, neither involving the sec-research/ skip-guard directly.

**Fault A — skip-guard scope is too narrow.** The guard at `publish.ps1:9-22` only skips when **100%** of changed paths are under `sec-research/`. Two of the four sec-research-era commits failed that test:

- `bf2df4e` — touched `.gitignore` and `docs/superpowers/specs/2026-05-07-sec-research-foundation-design.md` alongside sec-research files.
- `17ab8c8` — touched `.gitignore` and `publish.ps1` itself.

For each, `publish.ps1` ran the full pipeline including `publish_toolkit.py`, which `rmtree`d `site/content/docs/toolkit/` and rebuilt it from `.ai/`. Because `os.walk` writes file-by-file, **a partial / interrupted run leaves the dir half-empty** — exactly the present state, where only the alphabetically-first `skills/citation-seeker/SKILL.md` survived.

**Fault B — `publish_toolkit.py` is destructive-non-idempotent.** Even an uninterrupted run is a strict tear-down + rebuild rather than an additive sync. Any failure (Hugo build crash, Ctrl-C, encoding edge case, antivirus hold) between `rmtree` and the end of `publish_assets` leaves the working tree showing the survivors as `M` and the rest as `D` against HEAD — Garrett sees a "deletion" that is really an aborted regeneration.

The two faults reinforce: A makes the destructive script run when Garrett expected silence; B makes any partial failure look like targeted deletions.

## 3. Fix paths

### Path 1 — Tighten skip-guard to "any sec-research path implies skip"

Replace the all-must-match logic in `publish.ps1:11-17` with: "if **any** changed path starts with `sec-research/` and we are on `feature/sec-research-foundation` (or similar), skip." Stronger: skip whenever `sec-research/` appears in the diff at all.

- Files: `C:/Users/Garre/Workspace/publish.ps1` — **outside sec-research/**, requires PT-3 signed override.
- Trade-off: stops the bleeding immediately. Risk: if Garrett ever legitimately edits both site/ and sec-research/ in one commit, site/ changes won't publish until a follow-up commit. Acceptable — Stage-1 sec-research commits should not be sharing commits with site/ work anyway.

### Path 2 — Make `publish_toolkit.py` idempotent (no `rmtree`)

Replace `shutil.rmtree(TOOLKIT_OUTPUT)` at line 58-59 with an additive sync: walk both source and target, write only when content differs, optionally prune outputs that have no source counterpart at the **end** (after all writes succeed). Even simpler: just delete the `rmtree` call. Stale orphan files are a smaller harm than mass deletion-on-crash.

- Files: `C:/Users/Garre/Workspace/.ai/scripts/publish_toolkit.py` — **outside sec-research/**, requires PT-3 signed override.
- Trade-off: defends against future failure modes regardless of what triggers the publish. Doesn't address why publish ran at all on a sec-research-flavoured commit.

### Path 3 — Decouple `publish_toolkit.py` from post-commit

Move the `publish_toolkit.py` invocation out of `publish.ps1` and into a separate trigger: a manual `pnpm publish-toolkit`-style command, or a watcher that fires only when `.ai/skills/**` or `.ai/scripts/**` actually change.

- Files: `C:/Users/Garre/Workspace/publish.ps1` — outside sec-research/, PT-3 override.
- Trade-off: cleanest separation of concerns; toolkit republish becomes intentional. Higher implementation cost; needs a new entry point and habit change.

## 4. Recommended fix

**Stack Path 1 + Path 2.** Path 1 alone leaves the `rmtree`-then-crash footgun for any future site/-only commit. Path 2 alone leaves the publish loop firing whenever sec-research/ shares a commit with anything else, burning Firebase deploys for no doc change. Together they are defense-in-depth.

If only one is feasible: **Path 2**. The `rmtree` is the load-bearing destructive operation. Removing it neutralises the worst outcome of every other failure mode, including future skip-guard misses, and the fix is a single-line edit (delete or comment lines 58-59 of `publish_toolkit.py`).

Both fixes touch files outside `sec-research/`, so PT-3 will block. Garrett needs to run `python scripts/sign_override.py` (HMAC key at `~/.claude/sec-research-override-key`) and supply the token, or apply the edits manually outside of a Claude session.

## 5. Modified-not-deleted files

Three categories of `M` entries are unrelated to `publish_toolkit.py`:

- `site/content/docs/001-workspace-foundation.md`, `002-local-orchestration.md`, `003-local-script-autonomy.md` — regenerated by `.ai/scripts/generate_spec.py:68-70`. Same publish run, different script. The diff is the `date:` field re-stamped via `datetime.now()` plus mock metric values; content is otherwise template-driven.
- `site/content/docs/toolkit/skills/citation-seeker/SKILL.md` — written by `publish_toolkit.py` but not deleted because it was the last successful write before the run aborted (alphabetically-first skill, root-level file). Its diff shows `date: 2026-05-07` and a content-derivative description change, which is consistent with `.ai/skills/citation-seeker/SKILL.md` having been edited at `mtime 2026-03-31` against the `2026-03-30` snapshot in HEAD.
- `site/layouts/shortcodes/experiment-metrics.html` — manual hand-edit (adds a `Page.Resources.GetMatch "data.json"` fallback). Not produced by either script. Pre-existing uncommitted work.

So `publish_toolkit.py` accounts for 100% of the `D` entries plus 1 `M`; `generate_spec.py` accounts for 3 `M`; the shortcode `M` is independent.
