# Codex 00 — Setup

> Cleared 2026-08-17 · reviewed **3/3** · stat: `tooling`

## The one-line version

`uv` replaces the entire `pip` / `venv` / `pyenv` / `poetry` stack, `ruff` replaces
Black + isort + Flake8, and the red→green→review loop is the rhythm for every dungeon
after this one.

## Concepts

### The toolchain is lazy and reproducible

`uv run <cmd>` resolves and builds `.venv` from `pyproject.toml` + `.python-version`
on demand. There is no activation ritual — no `source .venv/bin/activate`, no
`poetry shell`. If the environment is stale, `uv run` fixes it before running.

### `sys.version_info` is a named tuple

It answers to `.major` / `.minor` **and** to indexing and slicing (`[:2]`), because
`namedtuple` is a `tuple` subclass with named fields bolted on. That duality shows up
again every time you meet one.

### `from __future__ import annotations`

Defers evaluation of annotations to strings, which is what lets `tuple[int, int]` and
`dict[str, str]` work as annotations on older interpreters without importing from
`typing`. On 3.12+ you mostly don't need it, but you'll see it everywhere.

### Import ordering is mechanical

`__future__` → stdlib → third-party → first-party → local, blank line between groups,
alphabetical within a group. You don't have to remember it — `ruff` enforces and fixes
it (`I001`).

## What you actually hit

- **Stale `TODO` docstring left behind.** The scaffolding comment stayed after the
  work was done, so it had become a lie. Kill the scaffolding in the same commit that
  satisfies it — this recurred in Modules 02 and 02b, so it's a real habit to build.

## Reference

| Topic | Docs |
|---|---|
| `sys.version_info` | [docs.python.org/3/library/sys.html#sys.version_info](https://docs.python.org/3/library/sys.html#sys.version_info) |
| `__future__` imports | [docs.python.org/3/library/\_\_future\_\_.html](https://docs.python.org/3/library/__future__.html) |
| Postponed annotation evaluation | [PEP 563](https://peps.python.org/pep-0563/) |
| Style guide | [PEP 8](https://peps.python.org/pep-0008/) |
| uv | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| ruff (linter) | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) |
| ruff (formatter) | [docs.astral.sh/ruff/formatter](https://docs.astral.sh/ruff/formatter/) |
| pytest | [docs.pytest.org](https://docs.pytest.org/en/stable/) |
