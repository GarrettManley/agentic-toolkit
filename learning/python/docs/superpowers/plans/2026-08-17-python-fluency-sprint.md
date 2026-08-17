# Python Fluency Sprint Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a self-paced, test-driven Python tutorial with a gamified progress engine (`sprint`) — delivering a runnable skeleton, the `sprint` XP/achievements/mastery CLI (with its own tests), and the first two modules (Setup, Data model). All later modules are generated on demand.

**Architecture:** The project is an installable `uv`/hatchling package exposing a `sprint` console script (`src/sprint/`). Each module is a self-contained dir (`README.md` + `exercise.py` stub + `test_exercise.py`); reference answers in `solutions/` are revealed via `sprint reveal` (which records a peek). `sprint` scores completions (XP, combo, streak, per-skill mastery), and `sprint next` picks what to reinforce — so the curriculum after Module 01 is data-driven, not fixed.

**Tech Stack:** Python ≥3.12, `uv` + `hatchling`, `ruff`, `pytest`, `mypy --strict` (on `src/sprint/`).

## Global Constraints

- **Python floor:** `>=3.12`, pinned via `learning/python/.python-version`.
- **Toolchain:** `uv` (env/deps/build), `ruff format` + `ruff check` (line-length **88**), `pytest` (AAA), `mypy --strict` on `src/sprint/`.
- **Typing:** type hints on all public signatures. `src/sprint/` is strict-typed.
- **Learning-mode contract:** the `sprint` engine and all scaffolding are authored here; the **load-bearing implementation in `exercise.py` is NEVER pre-filled** (it `raise NotImplementedError` at a `TODO`), and every stub has a matching `solutions/` reference proving it's solvable.
- **Determinism:** engine functions that need "today" take an injected `today: date | None = None`; no hidden globals — keeps `tests/` deterministic.
- **Per-module test run:** `uv run pytest modules/<NN-name> -v` (one module at a time under default prepend import mode; add `--import-mode=importlib` to run all at once).
- **Commit hygiene:** stage explicit files. Every commit under `learning/` carries `[verify-override: nested-clone-audit-hb-64f]` (workspace verify gate trips on the nested marketplace clone, hb-64f). These paths are outside `site/` `.ai/` `docs/` `README.md`, so the post-commit publish hook correctly skips.
- **Ledger is runtime state:** `.sprint/ledger.json` is git-ignored.

---

## File Structure

```text
learning/python/
├── README.md              # Task 1
├── pyproject.toml         # Task 1 — uv + hatchling; sprint entry point; ruff/pytest/mypy
├── .python-version        # Task 1 — "3.12"
├── src/sprint/            # Task 2 — the engine
│   ├── __init__.py
│   ├── catalog.py         # module list + skill tags + XP weights + built flag
│   ├── models.py          # Ledger, ModuleRecord, SkillMastery, Achievement dataclasses
│   ├── store.py           # atomic JSON load/save
│   ├── scoring.py         # XP formula, levels, combo, streak, mastery
│   ├── achievements.py    # curated badges + unlock predicates
│   ├── render.py          # pure ledger→string rendering
│   └── cli.py             # argparse subcommands
├── tests/                 # Task 2 — engine test suite
│   ├── test_scoring.py
│   ├── test_achievements.py
│   ├── test_store.py
│   ├── test_catalog.py
│   └── test_render.py
├── modules/
│   ├── 00-setup/          # Task 3
│   └── 01-data-model/     # Task 4
├── capstone/README.md     # Task 1 placeholder
└── solutions/             # Tasks 3–4 references
```

---

## Task 1: Skeleton + packaging

**Files:** Create `pyproject.toml`, `.python-version`, `README.md`, `capstone/README.md`, `solutions/README.md`, `src/sprint/__init__.py`; modify root `.gitignore` (ignore `.sprint/`).

**Interfaces:** Produces a `uv`/hatchling project where `uv sync` installs the `sprint` console script (entry `sprint.cli:main`). Module/solution/test dirs are excluded from the wheel.

- [ ] **Step 1: `.python-version`** → `3.12`

- [ ] **Step 2: `pyproject.toml`**

```toml
[project]
name = "python-fluency-sprint"
version = "0.1.0"
description = "Gamified, test-driven Python fluency tutorial."
requires-python = ">=3.12"
dependencies = []

[project.scripts]
sprint = "sprint.cli:main"

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6", "mypy>=1.11"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sprint"]

[tool.ruff]
line-length = 88
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
addopts = "-q"
python_files = ["test_*.py"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src/sprint"]
```

- [ ] **Step 3:** Create `src/sprint/__init__.py` (empty, with a one-line module docstring).

- [ ] **Step 4:** Root `README.md` — overview, prerequisites (`uv`), setup (`uv sync`), the module loop, the `sprint` commands, attempt-first/reveal note. (Detailed copy authored at build time; must document the exact loop: read brief → `pytest` red → implement → `pytest` green → `sprint done <mod>` → review → `sprint review`.)

- [ ] **Step 5:** `capstone/README.md` placeholder + `solutions/README.md` (reveal-gated, attempt-first note).

- [ ] **Step 6:** Add to root `learning/`-block in `c:\Users\Garre\Workspace\.gitignore`: `learning/**/.sprint/`.

- [ ] **Step 7:** `cd learning/python && uv sync` → expect `.venv` + `sprint` script installed, no build error. Verify `uv run sprint --help` prints usage (after Task 2; for Task 1 a stub `main` returning 0 is acceptable to prove wiring).

- [ ] **Step 8:** Commit (explicit files) with `[verify-override: nested-clone-audit-hb-64f]`.

---

## Task 2: The `sprint` engine (TDD)

Built test-first, inline, `mypy --strict` clean. Contracts below are firm; write the full implementation to satisfy the listed tests. Sub-steps are ordered by dependency.

**Contracts:**

```python
# models.py
@dataclass
class ModuleRecord:
    module_id: str
    status: str = "available"          # available | passed | cleared
    attempts: int = 0
    peeked: bool = False
    ruff_clean: bool | None = None
    review_score: int | None = None    # 0..3
    xp_awarded: int = 0
    completed_on: str | None = None     # ISO date

@dataclass
class SkillMastery:
    skill_id: str
    mastery: float = 0.0                # 0.0..1.0

@dataclass
class Ledger:
    xp: int = 0
    combo: int = 0
    streak_days: int = 0
    last_active: str | None = None       # ISO date
    modules: dict[str, ModuleRecord] = field(default_factory=dict)
    skills: dict[str, SkillMastery] = field(default_factory=dict)
    achievements: list[str] = field(default_factory=list)

# catalog.py
@dataclass(frozen=True)
class ModuleSpec:
    id: str; title: str; skills: tuple[str, ...]; base_xp: int; built: bool
CATALOG: list[ModuleSpec]   # 00,01 built=True; 02–07 built=False; capstone base_xp=300
def get(module_id: str) -> ModuleSpec
def built_modules() -> list[ModuleSpec]

# scoring.py
LEVELS: list[tuple[str, int]] = [("Novice",0),("Apprentice",150),("Journeyman",400),
                                 ("Pythonista",800),("Core Dev",1300),("Maintainer",1800)]
def level_for(xp: int) -> tuple[str, int, int | None]   # (name, floor, next_floor|None)
def module_xp(base: int, *, no_peek: bool, ruff_clean: bool,
              review_score: int | None, combo: int) -> int
    # bonus = 40*no_peek + 20*ruff_clean + 20*(review_score or 0)
    # mult  = min(1.5, 1 + 0.1*max(0, combo-1));  return base + round(bonus*mult)
def next_combo(prev: int, *, no_peek: bool) -> int      # prev+1 if no_peek else 0
def register_active_day(ledger: Ledger, today: date) -> int   # returns XP added (0 or 10)
def apply_mastery(ledger: Ledger, skills: Iterable[str], *,
                  no_peek: bool, review_score: int | None) -> None

# achievements.py
@dataclass(frozen=True)
class BadgeDef:
    id: str; name: str; description: str; unlocked: Callable[[Ledger], bool]
BADGES: list[BadgeDef]                          # the curated 10
def newly_unlocked(ledger: Ledger) -> list[BadgeDef]   # predicate true AND id not in ledger.achievements

# store.py
def load(path: Path) -> Ledger                  # fresh Ledger() if file missing
def save(path: Path, ledger: Ledger) -> None    # write path.with_suffix('.tmp') then os.replace

# render.py
def bar(frac: float, width: int = 10) -> str
def status_screen(ledger: Ledger) -> str
def skills_screen(ledger: Ledger) -> str
def achievements_screen(ledger: Ledger) -> str

# cli.py
def main(argv: list[str] | None = None) -> int
# status | done <mod> | reveal <mod> | review <mod> --score N | skills | achievements | next
```

- [ ] **Step 1 (models + store, test-first):** `tests/test_store.py` — save→load round-trips a Ledger with nested `ModuleRecord`/`SkillMastery`; missing file → `Ledger()`; save is atomic (no `.tmp` left behind). Implement `models.py` + `store.py` to green.
- [ ] **Step 2 (scoring, test-first):** `tests/test_scoring.py` — `level_for` at boundaries (0→Novice, 149→Novice, 150→Apprentice, 1800→Maintainer with next=None); `module_xp` base-only, all-bonuses, and combo cap (×1.5); `next_combo` increments/resets; `register_active_day` adds 10 once per new day and resets streak on a gap (injected `today`). Implement `scoring.py` to green.
- [ ] **Step 3 (catalog, test-first):** `tests/test_catalog.py` — ids unique; `00`/`01` built, `02`–`07` not; `get` raises `KeyError` on unknown; capstone base_xp 300. Implement `catalog.py`.
- [ ] **Step 4 (achievements, test-first):** `tests/test_achievements.py` — `first-green` unlocks after one passed module; `no-peek-novice` needs a no-peek clear; `centurion` at ≥1000 XP; `newly_unlocked` excludes ids already in `ledger.achievements`. Implement `achievements.py`.
- [ ] **Step 5 (render, test-first):** `tests/test_render.py` — `bar(0.0)`/`bar(1.0)` endpoints and width; `status_screen` contains level name + XP + a module count. Implement `render.py`.
- [ ] **Step 6 (cli):** wire subcommands over the above. `done <mod>`: run `pytest modules/<id>` via `subprocess`; if green, run `ruff check`; compute XP via `scoring`, update combo/streak/mastery/records, append `newly_unlocked`, persist, print deltas; refuse (non-zero exit) if tests red. `reveal <mod>`: print `solutions/<id>.py`, set `peeked=True`, persist. Smoke-test: `uv run sprint status` on a fresh ledger renders Level Novice.
- [ ] **Step 7:** `uv run mypy` clean; `uv run ruff check src tests` clean; `uv run pytest tests -v` green.
- [ ] **Step 8:** Commit (explicit files) with the override tag.

---

## Task 3: Module 00 — Setup

Gentle first module: verifies the toolchain and walks the red→green loop once. `check.py` has one small `TODO`. Mark `00` `built=True` in the catalog (already set in Task 2).

**Files:** `modules/00-setup/README.md`, `modules/00-setup/check.py`, `modules/00-setup/test_check.py`, `solutions/00-setup.py`.

- [ ] **Step 1: `test_check.py`**

```python
import sys

from check import environment_report, python_version


def test_pytest_is_working():
    assert True


def test_python_version_matches_interpreter():
    assert python_version() == (sys.version_info.major, sys.version_info.minor)


def test_python_is_3_12_or_newer():
    assert python_version() >= (3, 12)


def test_environment_report_has_expected_keys():
    assert set(environment_report()) >= {"python", "implementation"}
```

- [ ] **Step 2: `check.py` (stub)**

```python
"""Module 00 — environment smoke test. Fill in `python_version()`.

Run:  uv run python modules/00-setup/check.py
"""

from __future__ import annotations

import platform


def python_version() -> tuple[int, int]:
    """Return the interpreter's (major, minor).

    TODO: return (sys.version_info.major, sys.version_info.minor). Import sys.
    """
    raise NotImplementedError


def environment_report() -> dict[str, str]:
    major, minor = python_version()
    return {"python": f"{major}.{minor}", "implementation": platform.python_implementation()}


if __name__ == "__main__":
    for key, value in environment_report().items():
        print(f"{key:<16} {value}")
```

- [ ] **Step 3:** `uv run pytest modules/00-setup -v` → `test_pytest_is_working` passes; three fail (`NotImplementedError`).
- [ ] **Step 4: `solutions/00-setup.py`** — the two functions implemented (import `sys`; return the tuple).
- [ ] **Step 5:** Verify solution passes (copy over stub, run pytest green, restore stub via `git checkout`, confirm red again).
- [ ] **Step 6: `README.md`** — why uv/ruff/pytest/mypy; the exact loop; end with running `sprint done 00`.
- [ ] **Step 7:** Commit (explicit files) with override tag.

---

## Task 4: Module 01 — Data model

Teach the object model by hand-implementing equality/repr/hash/truthiness on a `Money` value type + the mutable-default trap. (Module 05 later shows `@dataclass` generating these.) Skills tagged in catalog: `data-model`, `equality`, `hashing`, `truthiness`, `mutable-defaults`.

**Files:** `modules/01-data-model/README.md`, `modules/01-data-model/exercise.py`, `modules/01-data-model/test_exercise.py`, `solutions/01-data-model.py`.

- [ ] **Step 1: `test_exercise.py`**

```python
from exercise import Money, running_total


def test_repr_round_trips_the_fields():
    assert repr(Money(500, "USD")) == "Money(cents=500, currency='USD')"


def test_equality_is_by_value_not_identity():
    a, b = Money(500, "USD"), Money(500, "USD")
    assert a == b
    assert a is not b


def test_different_currency_is_not_equal():
    assert Money(500, "USD") != Money(500, "EUR")


def test_equality_with_non_money_is_false_not_error():
    assert (Money(500, "USD") == "500") is False


def test_hash_matches_equality():
    a, b = Money(500, "USD"), Money(500, "USD")
    assert hash(a) == hash(b)
    assert {a, b} == {a}
    assert {a: "yes"}[b] == "yes"


def test_truthiness_zero_is_falsy():
    assert not Money(0, "USD")
    assert Money(1, "USD")


def test_running_total_does_not_leak_between_calls():
    assert running_total(Money(100)) == [Money(100)]
    assert running_total(Money(200)) == [Money(200)]


def test_running_total_appends_to_supplied_ledger():
    ledger = [Money(100)]
    result = running_total(Money(200), ledger)
    assert result == [Money(100), Money(200)]
    assert result is ledger
```

- [ ] **Step 2: `exercise.py` (stub)** — `Money.__init__(cents, currency="USD")` provided; `__repr__`, `__eq__` (return `NotImplemented` for non-Money), `__hash__`, `__bool__`, and `running_total(amount, ledger=None)` each raise `NotImplementedError` with a guiding docstring (incl. the None-sentinel hint for the mutable-default trap).
- [ ] **Step 3:** `uv run pytest modules/01-data-model -v` → all fail.
- [ ] **Step 4: `solutions/01-data-model.py`** — idiomatic reference:

```python
from __future__ import annotations


class Money:
    def __init__(self, cents: int, currency: str = "USD") -> None:
        self.cents = cents
        self.currency = currency

    def __repr__(self) -> str:
        return f"Money(cents={self.cents}, currency={self.currency!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return (self.cents, self.currency) == (other.cents, other.currency)

    def __hash__(self) -> int:
        return hash((self.cents, self.currency))

    def __bool__(self) -> bool:
        return self.cents != 0


def running_total(amount: Money, ledger: list[Money] | None = None) -> list[Money]:
    if ledger is None:
        ledger = []
    ledger.append(amount)
    return ledger
```

- [ ] **Step 5:** Verify solution passes (copy over stub → green → restore → red).
- [ ] **Step 6: `README.md`** — data model brief: names-vs-values, `is` vs `==`, opt-in equality + hash pairing, `__bool__`, the mutable-default trap; end with `sprint done 01`.
- [ ] **Step 7:** Commit (explicit files) with override tag.

---

## Dynamic module protocol (Modules 02–07 + capstone)

No fixed backlog — generated on demand. To author the next module:

1. `sprint next` / `sprint skills` → pick the lowest-mastery built skill or the next planned module.
2. Add/flip its `catalog.py` entry to `built=True` (with skill tags + base XP).
3. Author via the template: write `test_exercise.py` → typed `exercise.py` stub with `TODO`s → confirm **red** → write `solutions/<id>.py` and verify it goes **green** (copy-verify-restore) → write `README.md`.
4. Commit with the override tag. The learner then runs the loop and `sprint done <id>`.

Planned skill tags per module live in `catalog.py`; subjects firm up at authoring time (spec table is the guide). Capstone (`base_xp=300`) is authored at Module 07.

---

## Self-Review

**Spec coverage:** learner profile/goals/non-goals → README + constraints; learning model → README + Tasks 3–4 + constraints; toolchain (uv/hatchling/ruff/pytest/mypy) → Task 1; directory structure → File Structure + Tasks 1–2; **gamification subsystem** (architecture, scoring, levels, mastery, peek, CLI, badges) → Task 2 contracts + tests; module breakdown 00–01 → Tasks 3–4, 02–07 → Dynamic protocol; capstone → placeholder (Task 1) + Dynamic protocol; resolved decisions (dynamic cadence, sprint CLI, quality+arcade scoring, curated badges, reveal-gated solutions) → Tasks 1–2 + Dynamic protocol; first increment → Tasks 1–4. **Covered.**

**Placeholder scan:** `capstone/README.md` and modules 02–07 are spec-sanctioned deferrals with a concrete authoring protocol, not gaps. `TODO`s inside `check.py`/`exercise.py` are the learner's fill-in points, each backed by a verified reference solution. Engine contracts specify signatures + formulas + a test manifest (built inline TDD), not hand-waving.

**Type consistency:** `Money(cents:int, currency:str="USD")`, `running_total(amount, ledger=None)->list[Money]`, `python_version()->tuple[int,int]`, `environment_report()->dict[str,str]`, and every `sprint` contract signature are consistent across stubs, tests, solutions, and callers.
