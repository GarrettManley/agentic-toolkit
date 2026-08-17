# Module 00 — Setup

Goal: confirm your toolchain works and walk the red→green loop once. This module's
exercise is tiny on purpose — one `TODO` — because the real point is the *rhythm*.

## Why this toolchain

- **uv** — one fast tool for the interpreter, the virtualenv, and dependencies.
  Coming from `pip`/`venv`/`pyenv`/`poetry`: uv replaces all of them. `uv sync` reads
  `pyproject.toml` + `.python-version` and builds `.venv` reproducibly.
- **ruff** — formatter *and* linter in one (replaces Black, isort, Flake8). Fast.
- **pytest** — the test runner. Plain `assert`; no `self.assertEqual` boilerplate.
- **mypy** — static type checker; joins from Module 06.

## Do this

1. `uv sync`
2. `uv run pytest modules/00-setup -v` → one test passes, three fail.
3. Open `check.py` and implement the `python_version()` `TODO`.
4. `uv run pytest modules/00-setup -v` → all green.
5. `uv run python modules/00-setup/check.py` → prints your environment report.
6. `uv run sprint done 00` → banks your first XP.

That is the exact rhythm for every module. When you want the reference answer,
`uv run sprint reveal 00` (it records a peek — no shame, just data). Onward.
