---
title: SOLID + Clean Architecture workspace standard and gm-common shared library
date: 2026-10-29
status: approved
tracker: hb-w4h
---

# SOLID + Clean Architecture standard and shared-utility library for the Workspace

Tracks: hb-w4h (beads epic; waves are its four child tasks hb-w4h.1 to hb-w4h.4). Plan file:
`~/.claude/plans/i-m-looking-to-apply-curious-acorn.md`.

## Goal

Apply SOLID and Clean Architecture across every project under `C:\Users\Garre\Workspace` so
utilities are reused instead of rewritten, subagents follow one written standard, and new projects
start on it. Decided 2026-10-29: **standard forward plus library extraction only** (no layering
refactors of existing projects); the shared library is **its own git repo** checked out nested at
`Workspace/libs/gm-common`, consumed by path dependency inside the Workspace and by git tag outside.

## Why now (recon findings)

- Duplication is concentrated in Python: about a dozen utilities copied across System.Control,
  learning/python, apps/hw-dashboard, sec-research, Career, `Workspace/.claude/hooks` and the
  marketplace plugins (UTF-8 forcing, atomic write, hook stdin/stdout protocol, project/data-root
  resolution, frontmatter parsing, UTC timestamps, fail-soft subprocess, JSON/JSONL helpers, slugify).
- PowerShell repeats a transcript + `### EXIT n` sentinel block in six `C:\Users\Garre\scripts`
  scripts (that project already has `lib/*.psm1` with Pester tests).
- Rust and TypeScript do not duplicate across projects.
- Layering: aether-engine is Clean-shaped (ports, adapters, dependency-cruiser gate); System.Control
  and learning/python are protocol-based; mtga-companion has a one-way crate split but no traits;
  hw-dashboard, Career and `.ai/scripts` are procedural.
- No workspace-wide design standard exists. The delivery plugin's `constitution` slot is bound
  nowhere; no review persona checks dependency direction; `bootstrap_project.ps1` copies from an
  empty template.
- Constraints: marketplace plugins cannot import a shared package (vendoring with
  `ci/check-vendored-sync.py` is the only mechanism); `AGENTS.md` forbids premature abstraction, so
  the standard must say when an interface is earned.

## Goals

1. One written standard every subagent, reviewer and `/deliver` run reads as binding.
2. One shared Python package holding the utilities copied today, with the copies replaced.
3. A non-empty project template.
4. Enforcement that hard-fails where deterministic and binds the standard into review where not.

## Non-goals and anti-goals

- No layering refactor of mtga-companion, hw-dashboard, Career, sec-research, `.ai/scripts`
  (published to the site) or aether-engine.
- sec-research hooks stay self-contained (fail closed, no external dependency).
- Marketplace `init.ps1` status-line copies stay.
- Anti-goal: a standard that pushes interfaces everywhere. If a reviewer demands ports for pure
  in-process code with one implementation, the standard failed.

## Deliverable 1: the standard

Path `Workspace/docs/standards/solid-clean-architecture.md`; pointers in `Workspace/CLAUDE.md`
(which also gains the tests-in-sibling-files rule) and `.ai/context/conventions.md`. Sections:

1. **Dependency rule.** Four rings: domain <- application <- adapters (filesystem, process,
   network, DB, clock, hardware) <- entrypoints (CLI, hooks, daemons, servers). Imports point inward
   only. Per-language mapping for Python, Rust, TypeScript, PowerShell.
2. **Earned abstraction.** A protocol/trait/interface is introduced only at a boundary where the
   dependency is IO or where a second real implementation exists. A test double counts only for IO.
3. **SOLID** with workspace exemplars: SRP; OCP via registries (`System.Control/effects/registry.py`,
   aether `LLMProvider`); LSP via `_: type[Device] = MyDevice`; ISP via aether `WorldMapStore`;
   DIP via `DungeonMaster(deps)`.
4. **Clean Code rules already in force**: typed public APIs, docstrings, tests in sibling files,
   test pyramid, no handling for impossible cases, validate at boundaries only.
5. **Reuse rule.** Rule of Three moves a utility to gm-common; never copy from another project;
   vendoring only where packaging isolation forces it, with a byte-identity check.
6. **Reference layouts** per language (mandatory only for new projects and the template).
7. **Reviewer checklist**, kept word-for-word identical to the review persona's.

## Deliverable 2: gm-common

Private repo `GarrettManley/gm-common` at `Workspace/libs/gm-common` (untracked by the Workspace
allow-list `.gitignore`; location documented in `AGENTS.md`).

```
gm-common/
  pyproject.toml          # uv_build, requires-python >=3.11, zero runtime deps, mypy strict, ruff 88
  src/gm_common/
    text.py               # force_utf8()
    fs.py                 # atomic_write_text/json, load_json(path, default), read_jsonl, append_jsonl
    paths.py              # find_project_root(start, markers), data_root(app, env_var)
    clock.py              # utc_now_iso(), local_tz()
    proc.py               # run(cmd, timeout, cwd) fail-soft -> Result(ok, code, out, err)
    hooks.py              # read_event(max_bytes), emit_block/emit_warn/emit_system
    frontmatter.py        # parse_frontmatter(text) -> (dict, body), stdlib-only YAML subset
    slug.py               # slugify()
  tests/                  # one test module per source module
  tools/check_tests_separate.py
  CLAUDE.md
  .importlinter
```

Each module is lifted from the best existing copy (e.g. `force_utf8` from
`claude-marketplace/plugins/discipline/scripts/run_with_flags.py`, atomic write from
`learning/python/src/sprint/store.py`, `data_root` from
`claude-marketplace/plugins/learning/scripts/storage.py`, hook protocol from the discipline hooks'
`emit_*` plus `sec-research/hooks/common.py`). Semver `v0.x`, conventional commits.

## Deliverable 3: consumption

| Consumer | Mechanism |
|---|---|
| System.Control, learning/python, apps/hw-dashboard | `[tool.uv.sources]` path dependency; swap copies to imports. `uv sync` failing loudly without the clone is the intended signal. |
| `Workspace/.claude/hooks/*` | Not a consumer (root commit gate must survive a fresh clone). |
| `C:\Users\Garre\scripts` | Local extraction: `Invoke-WithTranscript` into `lib/Hardening.Common.psm1` with a Pester case; replace the six sentinel blocks. PowerShell stays out of gm-common. |
| claude-marketplace | Vendor `gm_common/hooks.py` and `text.py` verbatim as `plugins/discipline/scripts/gm_hooks.py` / `gm_text.py` (canonical) and into consumer plugins; extend `VENDORED_FILES`; new optional `check-vendored-sync.py --source <gm-common>` byte-compares the canonical pair (local `verify.sh` only). `run_with_flags.py` untouched. |
| sec-research scripts, Career | Later. |
| aether-engine | `Workspace/Roleplaying` gets the constitution binding; no library use. |

## Deliverable 4: enforcement

- **Constitution binding** in `.claude/delivery.local.md` for Workspace root, System.Control,
  mtga-companion, claude-marketplace, Roleplaying, sec-research, gm-common. Value is repo-relative
  (`docs/standards/solid-clean-architecture.md`, `../docs/...`, `../../docs/...`); never absolute,
  because the public Workspace repo tracks `.claude/`.
- **Persona** `review:architecture-conformance` (code diffs) in the marketplace: embeds the generic
  checklist with no project names, accepts an optional constitution path from `/deliver`, dispatched
  by `docs:adversarial-review-code` when any source file is in the diff. Never asks for an interface
  the earned-abstraction rule does not justify.
- **Deterministic gates (hard-fail)**: git-native pre-commit hook + installer for System.Control
  (`ruff check`, `mypy --strict src`, `lint-imports`, `check_tests_separate.py`); the Workspace root
  gate (`check_verify_before_commit.py`) extended to run `lint-imports` + `check_tests_separate.py`
  for learning/python and hw-dashboard when staged; mtga-companion `pre-push.ps1` gains the inline
  `#[cfg(test)] mod tests {` check; marketplace `verify.sh` runs `--source` when the sibling exists.
  import-linter contracts **describe today's layering** in existing repos; only gm-common and the
  template enforce the full ring contract.
- **Plan-level carry**: the reviewer checklist is pasted into plans' `## Global Constraints`.

## Deliverable 5: template and bootstrap

Populate `Workspace/.ai/templates/project-init/` with a Python skeleton (uv, py>=3.11, mypy strict,
ruff 88, pytest, gm-common path dep, import-linter ring contract, `src/<pkg>/{domain,app,adapters,cli}`,
`tests/`, `CLAUDE.md` stub, `.claude/delivery.local.md` with `constitution:`, `.gitignore`). Fix
`bootstrap_project.ps1` (`<pkg>` substitution, stop-on-error preference, no emoji).
Rust/TypeScript get `CLAUDE.md` + `delivery.local.md` stubs only.

## Left to the builder

Exact `gm_common` signatures; whether `frontmatter.py` absorbs the two minimal-YAML parsers;
import-linter contract wording per project; persona prose within the hard rule.

## Waves (one `/deliver` each, ask between)

1. Standard + bindings + persona (hb-w4h.1).
2. gm-common repo, tag `v0.1.0`, clone, `AGENTS.md` (hb-w4h.2).
3. Consumer swaps (hb-w4h.3).
4. Template + bootstrap + gates (hb-w4h.4).

## Acceptance

- Wave 1: `/deliver` in System.Control prints `constitution` bound in its resolved-slot table;
  `docs:adversarial-review-code` on a sample diff dispatches the new persona.
- Wave 2: `uv run ruff check`, `uv run mypy --strict src`, `uv run pytest`, `lint-imports` green in
  `libs/gm-common`.
- Wave 3: every consumer's own gate green (System.Control mypy+pytest; learning pytest; hw-dashboard
  pytest; marketplace `verify.sh` with and without the sibling path; Pester for `scripts/`); grep
  proves zero remaining copies in swapped `src/` trees (learner `modules/`/`solutions/` untouched).
- Wave 4: bootstrap a scratch project and run `uv sync`, `uv run pytest`, `lint-imports`,
  `check_tests_separate.py` green; System.Control hook blocks a deliberate inline-test commit and
  passes a clean one; mtga-companion `pre-push.ps1` still green.
