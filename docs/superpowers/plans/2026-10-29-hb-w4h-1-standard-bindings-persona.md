# Wave 1: Architecture Standard, Constitution Bindings, Review Persona — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Publish the workspace SOLID + Clean Architecture standard, bind it as the delivery `constitution` in six repos, and ship a code-diff review persona that enforces it.

**Why:** No review step in this workspace checks dependency direction or whether an interface is earned (`pr-review-toolkit:code-reviewer` scores CLAUDE.md style; no persona reads imports). Recon found a dozen Python utilities copied across six projects and no written design standard for subagents, and the delivery plugin's `constitution` slot is bound nowhere. Doing nothing leaves every future `/deliver` run and wave 2-4 of `hb-w4h` (library, consumer swaps, template, gates) with no standard to bind to. Wave 1 is that gate; it ships value on its own (a bound constitution plus a persona that flags outward imports today) and is the prerequisite the later waves attach to.

**Architecture:** One markdown standard in the public Workspace repo, pointed to from `Workspace/CLAUDE.md`, `.ai/context/conventions.md` and a one-line carry-over in `System.Control/CLAUDE.md` and `mtga-companion/CLAUDE.md`; six `.claude/delivery.local.md` bindings with repo-root-relative paths; one new `review:architecture-conformance` agent in the marketplace dev clone, dispatched by `docs:adversarial-review-code` (which gains a `--constitution` argument that the `deliver` skill forwards), landing via PR. The persona's `## Checklist` and the standard's `## Reviewer checklist` carry the same five items, pinned by a diff in verification.

**Tech Stack:** Markdown, YAML frontmatter, PowerShell 5.1/7 (`publish.ps1`, `_scripts/*.ps1`), Python 3 marketplace CI (`ci/*.py`, `plugins/review/scripts/review_cli.py`, pytest), git (Workspace on `master`, claude-marketplace on `main`, System.Control on `master`, mtga-companion on `main`).

**Spec:** `C:\Users\Garre\Workspace\docs\superpowers\specs\2026-10-29-solid-clean-workspace-standard-design.md` (Deliverable 1, Deliverable 4 "Constitution binding" + "Persona", Wave 1). Tracker: beads `hb-w4h.1` under epic `hb-w4h`; Task 0 also closes `hb-64f`. Adversarial plan review: sibling `.review.md` (30 findings, all CRITICAL/IMPORTANT resolved or deferred there).

## Global Constraints

- Never read, list, grep, or write anything under `C:\Users\Garre\Workspace\Duracell*` or `C:\Users\Garre\Workspace\malachite\`.
- **No worktree for the Workspace or marketplace work.** The Workspace repo's nested clones (`claude-marketplace`, `System.Control`, `mtga-companion`, `Roleplaying`) are untracked and would be absent from a worktree. Work in the main checkouts. Every implementer runs `git rev-parse --show-toplevel && git branch --show-current` before touching a file and confirms both match the task's stated repo and branch.
- **Repo and branch per task:**

  | Repo | Path | Branch | Lands by |
  |---|---|---|---|
  | Workspace (public) | `C:\Users\Garre\Workspace` | `feat/hb-w4h-1-architecture-standard` from `master` | ff-merge to `master` via the finishing-a-development-branch menu (Landing) |
  | claude-marketplace (public) | `C:\Users\Garre\Workspace\claude-marketplace` (dev clone; never `~\.claude\plugins\...`) | `feat/architecture-conformance-persona` from `main` (`origin/main` = `a452f7e`) | PR to `main` (`land-policy: pr`) |
  | System.Control | `C:\Users\Garre\Workspace\System.Control` | `master` (its convention; tree clean) | direct commit; push on authorization |
  | mtga-companion | `C:\Users\Garre\Workspace\mtga-companion` | `main`, via a throwaway worktree (active checkout is `feat/phase-4-slice-2-followups` mid-sprint; never commit there) | direct commit on `main`; push on authorization |
  | Roleplaying | `C:\Users\Garre\Workspace\Roleplaying` | n/a (`.claude/` is gitignored) | no commit |
  | home (`C:\Users\Garre`) | — | untouched this wave (`AGENTS.md` is wave 2's) | — |

- **Publish hook (verified).** `Workspace/.git/hooks/post-commit` runs `publish.ps1` (Hugo build + Firebase deploy of the *working tree*, which holds pre-existing uncommitted `site/**` edits) for any commit touching `site/*`, `.ai/*`, `docs/*` or `README.md`. The site generators read only `.ai/adr` and `.ai/scripts`, so nothing under `docs/` or `.ai/context` can reach the site; the publishing-privacy rule is not at stake. Task 0 adds a `WORKSPACE_SKIP_PUBLISH=1` valve to `publish.ps1`; **every `git commit` in the Workspace repo in this plan is run as `WORKSPACE_SKIP_PUBLISH=1 git commit ...`** and its output must show the valve's skip line.
- **Commit gate (verified).** `.claude/hooks/check_verify_before_commit.py` is a PreToolUse hook matching `git commit` in any Bash command, regardless of cwd (so nested-repo commits also run the Workspace audits; harmless once Task 0 lands). It runs `_scripts/pre_commit_audit.ps1` (fails on the literal token `TBD` in any `.md` it walks; `docs/superpowers/` is pruned, `docs/standards/`, `.claude/`, `sec-research/.claude/` are walked) and `_scripts/verify_workspace.ps1`. Today the audit descends into `claude-marketplace/` (eight tracked `.md` files contain the token) and fails every commit (bead `hb-64f`); Task 0 fixes the prune list first.
- Before every commit: `git diff --cached --name-only` must equal the files listed in that step and nothing else. Never `git add -A`. Never stage the pre-existing `site/**` or `learning/python/modules/**` modifications.
- Marketplace: conventional commits with plugin scope (`feat(review):`, `feat(docs):`, `feat(delivery):`, `chore(deliver):`); CHANGELOGs are written by `ci/release.py`, never by hand; `git fetch --tags` before any `ci/release.py` dry run; never bump versions by hand. Every marketplace `.md` referencing the standard uses a backticked path, never a markdown link (`ci/check-doc-links.py` would fail on an out-of-repo target).
- Discipline frontmatter lint applies to `docs/**/*.md` outside `docs/superpowers/`: the standard's frontmatter carries `status`, `author`, `created`, `diataxis`.
- `constitution:` values are **relative to the repo root (the directory holding `.claude/`)**: `docs/standards/solid-clean-architecture.md` at the Workspace root; `../docs/standards/solid-clean-architecture.md` in every depth-1 nested repo and in `sec-research/`. Never absolute, never a username. gm-common's binding is deferred to `hb-w4h.2`.
- The persona embeds the generic checklist with **no project, repo, or person names** (the marketplace is public). The five numbered checklist items below are the single source of truth; Task 1 and Task 4 copy them verbatim, and Task 5 diffs them.

  ```
  1. Dependency direction: does every new or changed import point inward (domain <- application <- adapters <- entrypoints)? Name the offending import.
  2. Earned abstraction: is every new protocol, trait, or interface at an IO boundary or backed by a second real implementation? Name any that is neither.
  3. Test placement: is every test in a sibling test file, never inline in an implementation file?
  4. Shared-library duplication: does the diff add a utility (e.g. UTF-8 forcing, atomic write, frontmatter parsing) that a shared library or the same repo already provides? Name the existing symbol.
  5. Composition at the entrypoint: are IO adapters constructed in the entrypoint (CLI, hook, daemon, server) and passed in, rather than instantiated inside domain or application code?
  ```

- Earned-abstraction rule, verbatim in both the standard and the persona: *A protocol, trait, or interface is introduced only at a boundary where the dependency is IO (process, network, filesystem, database, clock, randomness, hardware) or where a second real implementation exists. A test double counts as a second implementation only for IO. Pure in-process code with one implementation is called directly.*
- Tests live in sibling test files, never inline in implementation files (all languages). Test pyramid per `Workspace/CLAUDE.md`.
- Marketplace agent files need frontmatter `name` (== filename stem), `description`, `tools`, and a top-level heading (`ci/agent_contract.py`); `plugins/review/scripts/persona.py` additionally requires a `Pushback triggers`, a `NOT covered` and a `Severity rubric` section (bold-bullet or H2 form). `docs/skill-index.md` is generated (`python3 ci/gen-skill-index.py --write`) and CI fails when stale.
- CRLF: both repos have `core.autocrlf = true` and `persona.atomic_write` writes CRLF on Windows. Every cross-file comparison in this plan strips `\r` first.
- Scratchpad for backups and the throwaway worktree: `C:\Users\Garre\AppData\Local\Temp\claude\C--Users-Garre-Workspace\0cfca8f6-84ce-4a1b-bb6c-05319add1f78\scratchpad` (`$SCRATCH` below).

## Review Focus

1. A `constitution:` relative path that resolves from the repo root but not from a subdirectory the operator launches `/deliver` in — every binding's body states the path is root-relative, and Task 3 verifies each with `test -f` from its repo root after stripping `\r`.
2. The persona demanding a port for pure in-process code with one implementation (the spec's anti-goal) — Verification runs the persona text against a seeded diff containing one single-implementation Protocol and one outward import; it must flag the import. Correction at execution (controller ruling): a Protocol the diff *adds* with no IO and one implementation is itself an earned-abstraction violation, so flagging it is correct; the anti-goal probe is a second seeded diff with a concrete pure class used directly and sibling tests, on which the persona must request no interface.
3. Checklist drift between standard and persona — Task 5's diff fails the plan if the five items differ; Task 4's test pins the persona side in CI. A durable cross-repo gate is deferred to `hb-w4h.4` (see `.review.md` I26).
4. A `docs/` or `.ai/` commit deploying the dirty `site/` tree — Task 0's valve, and every Workspace commit step expects the skip line in its output.
5. `pre_commit_audit.ps1` rejecting a commit on a stray `TBD` in a walked file — Task 1, 2 and 3 grep every touched `.md` before committing.

---

### Task 0: Repair the two Workspace gates this plan trips

**Files:**
- Modify: `C:\Users\Garre\Workspace\publish.ps1` (top of file, before the sec-research guard)
- Modify: `C:\Users\Garre\Workspace\_scripts\pre_commit_audit.ps1:25` (`$prunePattern`)
- Commit (second): `docs/superpowers/specs/2026-10-29-solid-clean-workspace-standard-design.md`, `docs/superpowers/plans/2026-10-29-hb-w4h-1-standard-bindings-persona.md`, the sibling `.review.md`
- Repo/branch: Workspace, `feat/hb-w4h-1-architecture-standard`

**Interfaces:**
- Produces: the `WORKSPACE_SKIP_PUBLISH` env valve every later Workspace commit sets; an audit that exits 0 on the current tree.

- [x] **Step 1: Snapshot and branch**

Run: `cd /c/Users/Garre/Workspace && git status --short > "$SCRATCH/workspace-status-before.txt" && git switch -c feat/hb-w4h-1-architecture-standard master && git branch --show-current`
Expected: `feat/hb-w4h-1-architecture-standard`. The pre-existing modifications (`CLAUDE.md`, `site/**`, `learning/.../exercise.py`) carry over unstaged; the snapshot is the reference for the abort procedure.

- [x] **Step 2: Baseline the audits on the current tree (expected to fail today)**

Run: `cd /c/Users/Garre/Workspace && pwsh -NoProfile -File _scripts/pre_commit_audit.ps1; echo "audit=$?"; pwsh -NoProfile -File _scripts/verify_workspace.ps1; echo "verify=$?"`
Expected: `audit=1` with `TBD` hits under `claude-marketplace/` (and possibly `Career/`, `mtga-companion/target`); `verify=0`. Record the output.

- [x] **Step 3: Add the skip valve to `publish.ps1`** as the first executable lines:

```powershell
# Skip valve: WORKSPACE_SKIP_PUBLISH=1 lets a docs/.ai commit land without a live deploy
# (e.g. when site/ has unrelated uncommitted edits). The hook output names the skip, so it is auditable.
if ($env:WORKSPACE_SKIP_PUBLISH -eq '1') {
    Write-Host "Skip-publish valve: WORKSPACE_SKIP_PUBLISH=1 is set. No publish." -ForegroundColor Yellow
    exit 0
}
```

- [x] **Step 4: Extend the prune pattern in `_scripts/pre_commit_audit.ps1`** — add these segment names to the alternation on line 25: `claude-marketplace|mtga-companion|Career|libs|worktrees|target|\.venv`. Update the "Pruned (never descended)" comment block (lines 13-22) to list them with the reason "nested clone with its own gate" or "build output".

- [x] **Step 5: Verify both repairs**

Run: `cd /c/Users/Garre/Workspace && WORKSPACE_SKIP_PUBLISH=1 powershell.exe -NoProfile -File publish.ps1; echo "publish=$?"; pwsh -NoProfile -File _scripts/pre_commit_audit.ps1; echo "audit=$?"; pwsh -NoProfile -File _scripts/verify_workspace.ps1; echo "verify=$?"`
Expected: the skip line then `publish=0` (no Hugo/Firebase output); `audit=0`; `verify=0`.

- [x] **Step 6: Commit the gate repair**

```bash
cd /c/Users/Garre/Workspace && git add publish.ps1 _scripts/pre_commit_audit.ps1 && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "fix(scripts): prune nested clones and build output from the pre-commit audit; add publish skip valve (hb-64f)"
```
Expected: staged list is exactly the two files; the gate runs the repaired audit from the working tree and allows; post-commit prints `no publish-relevant paths` (neither file is a trigger path).

- [x] **Step 7: Commit the spec, plan and review file**

```bash
git add docs/superpowers/specs/2026-10-29-solid-clean-workspace-standard-design.md docs/superpowers/plans/2026-10-29-hb-w4h-1-standard-bindings-persona.md docs/superpowers/plans/2026-10-29-hb-w4h-1-standard-bindings-persona.md.review.md && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "docs(plans): add the hb-w4h design spec and the wave-1 plan with its adversarial review"
```
Expected: three files staged; commit output contains `Skip-publish valve`.

---

### Task 1: The standard document

**Files:**
- Create: `C:\Users\Garre\Workspace\docs\standards\solid-clean-architecture.md`
- Repo/branch: Workspace, `feat/hb-w4h-1-architecture-standard`

**Interfaces:**
- Consumes: spec Deliverable 1 sections 1-7; the five checklist items and the earned-abstraction rule from Global Constraints.
- Produces: the file path every later task binds or points to; the `## Reviewer checklist` section Task 5 diffs against the persona.

- [x] **Step 1: Confirm the exemplar paths exist**

Run: `cd /c/Users/Garre/Workspace && for f in System.Control/src/system_control/effects/registry.py Roleplaying/src/llm/provider.ts Roleplaying/src/world-map/store.ts; do test -f "$f" && echo "OK $f" || echo "MISSING $f"; done; grep -rln "interface LLMProvider" Roleplaying/src | head -3`
Expected: three `OK` lines. If `provider.ts` is `MISSING`, cite the file the grep returns instead.

- [x] **Step 2: Write the file with this frontmatter and these seven H2 sections in this order**

Frontmatter (exact keys): `title: SOLID and Clean Architecture standard`, `status: active`, `author: Garrett Manley`, `created: 2026-10-29`, `diataxis: reference`, `tracker: hb-w4h`.

Opening paragraph: what the standard governs (every project under the Workspace, new and touched code), what it does not do (no retrofits are required by it), and that `/deliver` reads it as the `constitution`.

1. `## 1. The dependency rule` — the four rings (domain <- application <- adapters <- entrypoints), one sentence defining each, "imports point inward only", and a four-row table mapping ring to Python (subpackage or module prefix), Rust (module or crate), TypeScript (directory), PowerShell (`.psm1` module vs `.ps1` entrypoint script).
2. `## 2. Earned abstraction` — the verbatim rule from Global Constraints, then two sentences on how it reconciles with `AGENTS.md`'s "avoid premature abstractions".
3. `## 3. SOLID, as practised here` — five short paragraphs, each naming one workspace exemplar from Step 1: SRP (one reason to change per module); OCP via registries (`System.Control/src/system_control/effects/registry.py`, aether `LLMProvider`); LSP via conformance assertions (`_: type[Device] = MyDevice`); ISP via narrow protocols (aether `WorldMapStore`); DIP via IO behind ports composed at the entrypoint (aether `DungeonMaster(deps)`).
4. `## 4. Clean code rules already in force` — six bullets: typed public APIs; substantive docstrings; tests in sibling files, never inline (Rust: `#[cfg(test)] mod tests;` with `foo/tests.rs`); the test pyramid (link `../../CLAUDE.md` "Testing strategy"); no handling for cases that cannot happen; validate only at system boundaries.
5. `## 5. Reuse rule` — Rule of Three (a utility needed by a third project moves to the shared library, `gm-common`); never copy a utility from another project; vendoring only where packaging isolation forces it, and then with a byte-identity check (`claude-marketplace/ci/check-vendored-sync.py` is the pattern). No wave or tracker references in this section.
6. `## 6. Reference layouts` — one fenced tree each (at most six lines each) for Python (`src/<pkg>/{domain,app,adapters,cli}` + `tests/`), Rust (`crates/core` pure + `crates/<entry>`; `foo.rs` + `foo/tests.rs`), TypeScript (`src/{domain,app,adapters}` + `src/<entry>.ts` + `tests/{unit,integration,contract}`), PowerShell (`lib/*.psm1` + `*.ps1` + `tests/*.Tests.ps1`), prefixed once: "mandatory for new projects and the template; descriptive for existing ones". No `##` inside the fences.
7. `## Reviewer checklist` — one sentence ("These five items are the `## Checklist` of the `review:architecture-conformance` persona in the garrettmanley marketplace; edit both or neither.") then the five numbered items from Global Constraints, verbatim.

- [x] **Step 3: Verify lint preconditions**

Run: `cd /c/Users/Garre/Workspace && grep -c "TBD" docs/standards/solid-clean-architecture.md; head -8 docs/standards/solid-clean-architecture.md | grep -cE "^(status|author|created|diataxis):"; grep -c "^## " docs/standards/solid-clean-architecture.md`
Expected: `0`, `4`, `7`.

- [x] **Step 4: Commit**

```bash
cd /c/Users/Garre/Workspace && git add docs/standards/solid-clean-architecture.md && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "docs(standards): add the SOLID + Clean Architecture workspace standard (hb-w4h.1)"
```
Expected: one file staged; gate allows (exit 0); output contains `Skip-publish valve`.

---

### Task 2: Pointers in `Workspace/CLAUDE.md` and `conventions.md`

**Files:**
- Modify: `C:\Users\Garre\Workspace\CLAUDE.md` (append after "Testing strategy")
- Modify: `C:\Users\Garre\Workspace\.ai\context\conventions.md` (new `## 4. Software design` + frontmatter)
- Repo/branch: Workspace, `feat/hb-w4h-1-architecture-standard`
- (The `System.Control/CLAUDE.md` and `mtga-companion/CLAUDE.md` carry-over lines are written and committed in Task 3 with those repos' bindings. `C:\Users\Garre\AGENTS.md` is not touched this wave.)

**Interfaces:**
- Consumes: Task 1's file path.
- Produces: nothing later tasks call.

- [x] **Step 1: Confirm the pending `CLAUDE.md` diff is only the testing-strategy section, then commit it on its own**

Run: `cd /c/Users/Garre/Workspace && git diff --stat CLAUDE.md && git diff CLAUDE.md | grep -E '^[+-][^+-]' | grep -vc "^+" `
Expected: one file, additions only (the `-` count is `0`), and every added line belongs to the `## Testing strategy (all projects under Workspace/)` section. **If any other hunk is present, stop and report; do not commit.** Then:

```bash
git add CLAUDE.md && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "docs(claude): record the Workspace testing strategy (test pyramid, 2026-10-26)"
```
Expected: `CLAUDE.md` only; gate allows (an LF-to-CRLF warning is noise).

- [x] **Step 2: Append to `Workspace/CLAUDE.md`** a section `## Architecture standard (all projects under Workspace/)` with: a link to `docs/standards/solid-clean-architecture.md`; one sentence that `/deliver` binds it as `constitution` and `review:architecture-conformance` measures diffs against its checklist; one bullet with the tests-in-sibling-files rule (Rust form included). Do not copy the earned-abstraction rule here (two pinned copies exist already).

- [x] **Step 3: Add to `.ai/context/conventions.md`** a `## 4. Software design` section (sections 1-3 exist) with two bullets (the standard's path; "the reviewer checklist there is the architecture gate for every `/deliver` run"), and update frontmatter `last_verified: 2026-10-29`, `evidence: "docs/standards/solid-clean-architecture.md committed on feat/hb-w4h-1-architecture-standard, 2026-10-29"`, `model_used:` the executing model's name.

- [x] **Step 4: Verify**

Run: `cd /c/Users/Garre/Workspace && grep -c "docs/standards/solid-clean-architecture.md" CLAUDE.md .ai/context/conventions.md; grep -c "TBD" CLAUDE.md .ai/context/conventions.md`
Expected: first command `1` or more per file; second command `0` per file.

- [x] **Step 5: Commit**

```bash
git add CLAUDE.md .ai/context/conventions.md && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "docs: point CLAUDE.md and conventions at the architecture standard (hb-w4h.1)"
```
Expected: two files; gate allows; output contains `Skip-publish valve`.

---

### Task 3: Constitution bindings (Workspace root, sec-research, System.Control, mtga-companion, Roleplaying)

**Files and values:**

| Repo | File | `constitution:` value | Also | Git action |
|---|---|---|---|---|
| Workspace root | `.claude/delivery.local.md` (create) | `docs/standards/solid-clean-architecture.md` | — | own commit on the Workspace branch |
| sec-research | `sec-research/.claude/delivery.local.md` (create) | `../docs/standards/solid-clean-architecture.md` | body adds: "Applies when Claude is launched inside `sec-research/`; a Workspace-root session reads the root binding instead." | own commit on the Workspace branch (sec-research-only commit; the root gate skips it by design; sec-research's scope rule governs writes *outside* its dir, so this write is in scope) |
| System.Control | `.claude/delivery.local.md` (create) | `../docs/standards/solid-clean-architecture.md` | append to `System.Control/CLAUDE.md` after line 13: `The parent workspace's architecture standard (`../docs/standards/solid-clean-architecture.md`) is explicitly carried over and binding here; `/deliver` reads it as the constitution.` | one commit on `master` |
| mtga-companion | `.claude/delivery.local.md` (create; `.claude/` dir is new) | `../docs/standards/solid-clean-architecture.md` | append one bullet to `mtga-companion/CLAUDE.md`'s rule list: `Architecture standard: `../docs/standards/solid-clean-architecture.md` (dependency rule, earned abstraction, tests in sibling files) is binding; `/deliver` reads it as the constitution.` | one commit on `main` via a throwaway worktree |
| Roleplaying | `.claude/delivery.local.md` (exists; gitignored) | `../docs/standards/solid-clean-architecture.md` | backup first | no commit |
| claude-marketplace | `.claude/delivery.local.md` (exists; tracked) | `../docs/standards/solid-clean-architecture.md` | — | **done in Task 4 Step 2** on the marketplace branch |
| gm-common | — | — | deferred to `hb-w4h.2` | — |

**Interfaces:**
- Consumes: Task 1's file path.
- Produces: `constitution:` resolved by the `deliver` skill at step 1 of every run in these repos.

- [x] **Step 1: Write the four new files.** Frontmatter, exactly (substitute the value from the table):

```yaml
---
# delivery@garrettmanley config. Read by the `deliver` skill at the start of every /deliver run.
# Paths are relative to this repo's root (the directory holding .claude/). Other slots take the defaults.
constitution: <value from the table>
---
```
Body: one sentence naming the file as the SOLID + Clean Architecture standard that plan and code review are measured against (plus the sec-research sentence from the table). No `TBD`. The two `CLAUDE.md` carry-over lines from the table are written in the same step.

- [x] **Step 2: Roleplaying (gitignored): back up, then insert only if absent**

```bash
R=/c/Users/Garre/Workspace/Roleplaying/.claude/delivery.local.md; cp "$R" "$SCRATCH/Roleplaying-delivery.local.md.bak"
grep -q '^constitution:' "$R" && echo "already bound" || sed -i '0,/^---$/!{0,/^---$/s|^---$|# Constitution: the parent workspace architecture standard, relative to this repo root.\nconstitution: ../docs/standards/solid-clean-architecture.md\n---|}' "$R"
grep -n '^constitution:' "$R"
```
Expected: the backup exists; exactly one `constitution:` line inside the frontmatter (if `sed` leaves the file malformed, restore from the backup and insert the two lines by hand before the closing `---`).

- [x] **Step 3: Verify every binding resolves from its repo root**

```bash
for r in /c/Users/Garre/Workspace /c/Users/Garre/Workspace/sec-research /c/Users/Garre/Workspace/System.Control /c/Users/Garre/Workspace/mtga-companion /c/Users/Garre/Workspace/Roleplaying; do p=$(grep -m1 '^constitution:' "$r/.claude/delivery.local.md" | sed 's/constitution: *//' | tr -d '\r'); test -f "$r/$p" && echo "OK $r" || echo "MISSING $r -> $p"; done
grep -c "TBD" /c/Users/Garre/Workspace/.claude/delivery.local.md /c/Users/Garre/Workspace/sec-research/.claude/delivery.local.md
cd /c/Users/Garre/Workspace && git check-ignore -v .claude/delivery.local.md sec-research/.claude/delivery.local.md; echo "ignored=$?"
```
Expected: five `OK` lines (the marketplace is checked in Task 4); `0` and `0`; `ignored=1` (neither file ignored).

- [x] **Step 4: Commit — Workspace root, then sec-research, each alone**

```bash
cd /c/Users/Garre/Workspace && git add .claude/delivery.local.md && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "chore(deliver): bind the architecture standard as the Workspace constitution (hb-w4h.1)"
git add sec-research/.claude/delivery.local.md && git diff --cached --name-only
WORKSPACE_SKIP_PUBLISH=1 git commit -m "chore(deliver): bind the architecture standard as sec-research's constitution (hb-w4h.1)"
```
Expected: two commits, one file each; the second prints `Workspace verify gate skipped: sec-research/-only`. If a sec-research hook blocks the write or the commit, report its message and stop (do not override).

- [x] **Step 5: Commit — System.Control on `master`**

```bash
cd /c/Users/Garre/Workspace/System.Control && git branch --show-current && git status --short && git add .claude/delivery.local.md CLAUDE.md && git diff --cached --name-only
git commit -m "chore(deliver): bind the Workspace architecture standard as constitution; carry it over in CLAUDE.md (hb-w4h.1)"
```
Expected: `master`, clean before staging, exactly the two files.

- [x] **Step 6: Commit — mtga-companion on `main` via a throwaway worktree**

```bash
cd /c/Users/Garre/Workspace/mtga-companion && git worktree add "$SCRATCH/mtga-main" main
# write .claude/delivery.local.md and the CLAUDE.md bullet inside "$SCRATCH/mtga-main"
cd "$SCRATCH/mtga-main" && git add .claude/delivery.local.md CLAUDE.md && git diff --cached --name-only
git commit -m "chore(deliver): bind the Workspace architecture standard as constitution; carry it over in CLAUDE.md (hb-w4h.1)"
cd /c/Users/Garre/Workspace/mtga-companion && git worktree remove "$SCRATCH/mtga-main" && git log main -1 --oneline && git branch --show-current
```
Expected: the commit is on `main`; the active checkout is still `feat/phase-4-slice-2-followups` with a clean tree. No cargo command runs.

---

### Task 4: `review:architecture-conformance` persona (marketplace)

**Files:**
- Create: `plugins/review/agents/architecture-conformance.agent.md` (via scaffold)
- Create: `plugins/review/tests/test_architecture_conformance.py`
- Modify (count sites, all cosmetic but all required): `plugins/review/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (both description strings: `16 archetype agents` -> `17`, add `architecture-conformance` to the enumerated list; keep the two strings identical), `plugins/review/README.md` (line 18 `16` -> `17`; line 22 `Sixteen` -> `Seventeen`; new agents-table row), root `README.md` (`sixteen` -> `seventeen`), `plugins/review/skills/reviewer-personas/SKILL.md` (line 16 count; selection table: new row `| Code diffs / PRs touching source files | Add `review:architecture-conformance` |`), `ci/tests/test_agent_contract.py` (line 43 comment `16` -> `17`; line 45 floor `>= 20` -> `>= 21`), `docs/skill-index.md` (regenerated)
- Modify: `.claude/delivery.local.md` (the marketplace binding, own commit)
- Leave alone: `docs/plugin-schema-gotchas.md:128` (a dated verification record), all CHANGELOGs (`release.py` writes them)
- Repo/branch: claude-marketplace, `feat/architecture-conformance-persona` from `main`

**Interfaces:**
- Consumes: the five checklist items and the earned-abstraction rule from Global Constraints.
- Produces: `subagent_type: review:architecture-conformance`, consumed by Task 5's dispatch row.

- [x] **Step 0: Baseline the marketplace gates on clean `main`**

Run: `cd /c/Users/Garre/Workspace/claude-marketplace && git status --short && python3 --version && python3 -m pytest plugins/review/tests -q && python3 -m pytest ci/tests -q && bash scripts/verify.sh`
Expected: clean tree; a Python 3 version; both suites pass; every stage `[verify] OK`. Record the output. If `python3` is not on PATH in Git Bash, say so and run the same with `python` (the user hooks use `python`).

- [x] **Step 1: Branch, scaffold, and bind**

Run: `git switch -c feat/architecture-conformance-persona main && python3 plugins/review/scripts/review_cli.py scaffold architecture-conformance --description "Use when reviewing a code diff or PR for dependency direction, earned abstraction, test placement, and duplication of shared-library utilities. Catches imports that point outward, interfaces with no IO boundary and no second implementation, inline test modules, and re-implemented utilities." --apply --agents-dir plugins/review/agents`
Expected: a line starting `scaffolded architecture-conformance ->` naming the new file (Windows path separators and a trailing "Fill its pushback triggers" sentence are fine).

- [x] **Step 2: Add the marketplace binding and commit it alone**

Insert into the existing frontmatter of `.claude/delivery.local.md`: a comment line `# Constitution: the parent workspace architecture standard, relative to this repo root (unresolvable on other clones; deliver warns and treats it as unset).` and `constitution: ../docs/standards/solid-clean-architecture.md`. Backticked path only, no markdown link.

```bash
p=$(grep -m1 '^constitution:' .claude/delivery.local.md | sed 's/constitution: *//' | tr -d '\r'); test -f "$p" && echo OK
git add .claude/delivery.local.md && git diff --cached --name-only && git commit -m "chore(deliver): bind the parent workspace architecture standard as constitution (hb-w4h.1)"
```
Expected: `OK`; one file in the commit.

- [x] **Step 3: Write the failing tests** `plugins/review/tests/test_architecture_conformance.py`:

```python
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
PERSONA = AGENTS_DIR / "architecture-conformance.agent.md"


def _checklist_items(text: str) -> list[str]:
    section = text.split("## Checklist", 1)[1]
    return [line.strip() for line in section.splitlines() if line.strip()[:2] in {"1.", "2.", "3.", "4.", "5."}]


def test_persona_pins_the_earned_abstraction_rule():
    text = PERSONA.read_text(encoding="utf-8")
    assert "introduced only at a boundary where the dependency is IO" in text


def test_persona_checklist_has_exactly_five_items():
    text = PERSONA.read_text(encoding="utf-8")
    assert "## Checklist" in text
    assert [item[:2] for item in _checklist_items(text)] == ["1.", "2.", "3.", "4.", "5."]
```

- [x] **Step 4: Run them to verify they fail** — `python3 -m pytest plugins/review/tests/test_architecture_conformance.py -q` — Expected: 2 failed (the scaffold has neither the phrase nor a `## Checklist`).

- [x] **Step 5: Fill the persona body, keeping the scaffold's bold-bullet shape.** Frontmatter: `name: architecture-conformance`, the Step 1 description, `tools: Read, Grep, Glob, Bash`. Title line `# Architecture Conformance — reads the imports, not the prose`. Fill every scaffold bullet:
  - **Cares about:** the dependency rule and earned abstraction.
  - **Knowledge:** Clean Architecture rings; Python/Rust/TypeScript/PowerShell import and module conventions; out of depth on style, naming, error handling, performance.
  - **Pushback triggers:** as bullets (never a numbered list): an import from an inner ring to an outer one; a new protocol/trait/interface with no IO behind it and one implementation; a test module inside an implementation file; a re-implemented utility the repo or its shared library already has; an adapter instantiated inside domain or application code.
  - **Behavioral rules** (add as a bold bullet with sub-bullets): the earned-abstraction rule verbatim; "Never asks for an interface the earned-abstraction rule does not justify"; "When a `--constitution <path>` is given in the prompt, read it and cite its section numbers; otherwise apply the checklist alone"; "Does not flag style, naming, or error handling (code-reviewer and silent-failure-hunter own those)".
  - **NOT covered:** style/naming, error handling, test *quality* (test-strategy), performance.
  - **Severity rubric:** `blocker` = outward import, or inline tests in a new file; `must_fix` = unearned interface or duplicated utility; `nit` = composition inside application code with one call site; `signal` = a second implementation about to appear; `praise` = an adapter extracted at an IO boundary with its test double.
  - **Source:** `Archetype — scaffolded 2026-10-29 from the workspace architecture standard; refine from review catches.` **Last updated:** `2026-10-29 — initial archetype.`
  - Then an H2 `## Checklist` as the last section, whose body is the five items from Global Constraints verbatim. This is the only numbered list in the file.
  - No project, repo, or person names anywhere in the file.

- [x] **Step 6: Update the count sites and regenerate the index** per the Files list; then `python3 ci/gen-skill-index.py --write`.

Run: `grep -rn "16 archetype\|Sixteen\|sixteen\|16 review" --include=*.md --include=*.json --include=*.py . | grep -v CHANGELOG | grep -v plugin-schema-gotchas; echo "stale=$?"`
Expected: `stale=1` (no hits).

- [x] **Step 7: Run the gates**

Run: `python3 -m pytest plugins/review/tests -q && python3 -m pytest ci/tests -q && python3 ci/gen-skill-index.py --check && bash scripts/verify.sh`
Expected: both suites pass including the two new tests; `up to date`; every stage `[verify] OK`.

- [x] **Step 8: Commit**

```bash
git add plugins/review/agents/architecture-conformance.agent.md plugins/review/tests/test_architecture_conformance.py plugins/review/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/review/README.md README.md plugins/review/skills/reviewer-personas/SKILL.md ci/tests/test_agent_contract.py docs/skill-index.md && git diff --cached --name-only
git commit -m "feat(review): add architecture-conformance code-diff persona (hb-w4h.1)"
```
Expected: exactly the nine files.

---

### Task 5: Dispatch the persona from `docs:adversarial-review-code`; forward the constitution from `deliver`

**Files:**
- Modify: `plugins/docs/skills/adversarial-review-code/SKILL.md` — frontmatter `description` (add "and architecture conformance (dependency direction, earned abstraction)"), `## Interface` block + Arguments table (new `--constitution <path>`), Step 1 bullets (lines 49-50), Step 2 table (lines 61-65), `## Cross-references` (soft prerequisite)
- Modify: `plugins/delivery/skills/deliver/SKILL.md` step 10 (line 342-343)
- Modify: `docs/skill-index.md` (regenerated; the description changed)
- Repo/branch: claude-marketplace, `feat/architecture-conformance-persona`

**Interfaces:**
- Consumes: Task 4's `review:architecture-conformance`.
- Produces: `--constitution <path>` on `adversarial-review-code`, forwarded by `deliver` step 10.

- [x] **Step 1: Interface** — add `[--constitution <path>]  # governance doc forwarded to agents that accept one` to the usage block and a row `| `--constitution` | unset | Path to a governance document; forwarded to `review:architecture-conformance`, which cites its section numbers |` to the Arguments table.

- [x] **Step 2: Step 1 bullets** — add after the `type-design-analyzer` bullet: "If any `.py`, `.rs`, `.ts`, `.tsx`, `.cs`, `.ps1`, `.psm1`, `.mjs` or `.js` file appears in the diff and the `review` plugin is installed, include `review:architecture-conformance`; if the plugin is absent, print `architecture-conformance: review plugin not installed — skipped` and continue."

- [x] **Step 3: Step 2 table** — add row `| `review:architecture-conformance` | Dependency direction, earned abstraction, test placement, shared-library duplication (source files only; receives `--constitution` when given) |`. Cross-references: add `- **Soft prerequisite:** `review` (`garrettmanley`) for the architecture-conformance dispatch; skipped with a printed note when absent.`

- [x] **Step 4: `deliver` step 10** — change "treat it as binding context the diff is measured against, in addition to the standard review." to "treat it as binding context the diff is measured against, in addition to the standard review, and pass its path as `--constitution` so `review:architecture-conformance` reads it."

- [x] **Step 5: Regenerate the index and verify the two documents agree**

```bash
cd /c/Users/Garre/Workspace/claude-marketplace && python3 ci/gen-skill-index.py --write && git diff --stat docs/skill-index.md
diff <(sed -n '/^## Reviewer checklist/,/^## /p' /c/Users/Garre/Workspace/docs/standards/solid-clean-architecture.md | tr -d '\r' | grep -E '^[1-5]\. ') <(sed -n '/^## Checklist/,$p' plugins/review/agents/architecture-conformance.agent.md | tr -d '\r' | grep -E '^[1-5]\. ') && echo IDENTICAL
git diff main -- plugins/docs plugins/delivery docs/skill-index.md | grep '^+' | grep -n -i "Garre\|System.Control\|mtga\|aether\|sec-research\|gm-common\|hb-w4h\|Roleplaying"; echo "leak=$?"
python3 ci/gen-skill-index.py --check && bash scripts/verify.sh
```
Expected: `IDENTICAL` with no diff lines; `leak=1`; `up to date`; all `[verify] OK`.

- [x] **Step 6: Commit (two commits, plugin-scoped)**

```bash
git add plugins/docs/skills/adversarial-review-code/SKILL.md docs/skill-index.md && git diff --cached --name-only && git commit -m "feat(docs): dispatch review:architecture-conformance on source diffs; add --constitution (hb-w4h.1)"
git add plugins/delivery/skills/deliver/SKILL.md && git diff --cached --name-only && git commit -m "feat(delivery): forward the constitution path to adversarial-review-code (hb-w4h.1)"
```

---

## Verification

Run after all tasks; record command, output and exit code under each line (Iron Law evidence):

Evidence (raw output, exit codes, both probes) is recorded in the sibling file `2026-10-29-hb-w4h-1-standard-bindings-persona.evidence.md`; every line below passed on 2026-10-29.

- [x] Workspace branch: `git log master..HEAD --format=%s` lists exactly these subjects in order: `fix(scripts): …(hb-64f)`, `docs(plans): …`, `docs(standards): …`, `docs(claude): record the Workspace testing strategy …`, `docs: point CLAUDE.md and conventions …`, `chore(deliver): … Workspace constitution …`, `chore(deliver): … sec-research's constitution …` (7 planned subjects; 9 commits on the branch because Task 0 and Task 1 each took one review-fix commit — `fix(scripts): escape .venv …` and `docs(standards): fix the DIP exemplar …` — plus this evidence commit). `git status --short` equals `$SCRATCH/workspace-status-before.txt` minus `CLAUDE.md`.
- [x] `cd /c/Users/Garre/Workspace && pwsh -NoProfile -File _scripts/pre_commit_audit.ps1 && pwsh -NoProfile -File _scripts/verify_workspace.ps1 && echo BOTH_OK` prints `BOTH_OK`.
- [x] Task 3 Step 3's loop extended with `/c/Users/Garre/Workspace/claude-marketplace` prints six `OK`.
- [x] Marketplace branch: `git log main..HEAD --format=%s` shows the four planned commits (`chore(deliver)`, `feat(review)`, `feat(docs)`, `feat(delivery)`) plus one review-fix commit (`fix(review): make the architecture-conformance rubric decidable …`); `python3 -m pytest plugins/review/tests -q`, `python3 -m pytest ci/tests -q`, `python3 ci/gen-skill-index.py --check`, `bash scripts/verify.sh` all pass; `git fetch --tags && python3 ci/release.py --dry-run` includes minor bumps for `review`, `docs` and `delivery` (report any other plugin it proposes).
- [x] Task 5 Step 5's diff prints `IDENTICAL`; `grep -n -i "Garre\|System.Control\|mtga\|aether\|sec-research\|gm-common\|hb-w4h\|Roleplaying" plugins/review/agents/architecture-conformance.agent.md` prints nothing.
- [x] Spec acceptance 1 (constitution bound): paste the hand-resolved slot table for `System.Control` (read `System.Control/.claude/delivery.local.md`; all slots default except `constitution = ../docs/standards/solid-clean-architecture.md`) verbatim under this line.
- [x] Spec acceptance 2, pre-release proxy (persona behaviour): write `$SCRATCH/seed.diff` adding `src/shop/domain/order.py` that (a) imports `from shop.cli.main import print_receipt` and (b) defines `class Pricer(Protocol)` with one in-process implementation `FlatPricer` and no IO. Dispatch one `general-purpose` agent (model `sonnet`) whose prompt is the full text of `architecture-conformance.agent.md` followed by the diff and "Review this diff; emit findings in your severity vocabulary." Expected: a `blocker` naming the outward import; **no** `must_fix` or `blocker` for `Pricer`. Paste the agent's findings here. Live dispatch through `/adversarial-review-code` is only possible after the marketplace release is installed (Landing) and is recorded there.

## Landing

Order: Workspace first (so the standard exists on `master` before anything points at it), then System.Control and mtga-companion (already committed on their main branches), then the marketplace PR.

- **Workspace:** present the `superpowers:finishing-a-development-branch` menu; the proposed command is `git switch master && git merge --ff-only feat/hb-w4h-1-architecture-standard` (a fast-forward runs no `post-commit`, so no deploy). `git push` only on explicit authorization (public remote). Kill switch for a bad standard: delete the `constitution:` line from a binding.
- **System.Control / mtga-companion:** `git push` on explicit authorization; otherwise report the two unpushed commits.
- **Marketplace:** `gh pr create --base main --title "feat(review,docs,delivery): architecture-conformance persona + constitution dispatch (hb-w4h.1)"` with a body listing the four commits and the no-names check. Merge on approval. Release is a separate, later step (`git fetch --tags && python3 ci/release.py --dry-run`, then `--apply` per the repo's release procedure): release `review` before or together with `docs` and `delivery` (an older `review` lacks the persona the new `docs` references; the skip note covers absence only). **The persona is not live until the release is tagged and the plugin cache reinstalled**; record the first live `docs:adversarial-review-code` dispatch under Verification acceptance 2 when that happens.
- **Trackers:** `bd close hb-w4h.1` and `bd close hb-64f` (note: prune list extended in `fix(scripts)` commit) after the Workspace merge and PR merge; then `retrospective:plan-retrospective` by explicit path (plan mode tracks the epic plan file, not this one).

## Abort and rollback

- **Workspace, before merge:** `git switch master && git branch -D feat/hb-w4h-1-architecture-standard`. The pre-existing unstaged modifications are never staged by this plan and survive the switch. If Task 2 Step 1 committed `CLAUDE.md`, that commit is on the branch and goes with it (the diff returns to the working tree only if cherry-picked back; re-apply from `git show <sha>` if needed).
- **Workspace, after a failed gate mid-branch:** fix and re-run the step; never `--amend` across the gate, never `[verify-override]` for this plan's commits.
- **System.Control / mtga-companion:** `git revert <sha>` on `master` / `main` (one doc commit each); if unpushed, `git reset --hard HEAD~1` is also acceptable on a clean tree.
- **Roleplaying:** `cp "$SCRATCH/Roleplaying-delivery.local.md.bak" Roleplaying/.claude/delivery.local.md`.
- **Marketplace:** close the PR and `git branch -D feat/architecture-conformance-persona`; nothing live changes until release.
- **Partial state is safe:** a binding that points at a missing file makes `deliver` warn and treat `constitution` as unset; a persona with no dispatch row is inert; a dispatch row for an uninstalled persona prints the skip note.

## Retrospective

Written after landing via `retrospective:plan-retrospective` by explicit path (plan-mode tracks the epic plan file, not this one).

**Completion (2026-10-29):** Tasks 0-5 complete and task-reviewed (two fix rounds total: Task 0 `.venv` escape, Task 4 rubric decidability). Workspace branch `feat/hb-w4h-1-architecture-standard` (unmerged, unpushed); System.Control `master` 443ccad and mtga-companion `main` 88e59d4 committed, unpushed; Roleplaying binding edited (gitignored); marketplace branch `feat/architecture-conformance-persona` (five commits, PR not yet opened). Landing and tracker closure await authorization per the Landing section.
