---
date: 2026-08-17
status: approved
revision: v2
topic: learning/python tutorial
audience: experienced developer new to Python
---

# Python Fluency Sprint — Design Spec

## Purpose

A self-paced, test-driven tutorial that takes an **experienced developer who is new
to Python** to **idiomatic fluency** — the ability to write Python a Pythonista would
recognize as idiomatic, not merely working. It is breadth-first across Python's data
model, idioms, typing, testing, and packaging, converging into one real capstone build.

Progress is tracked and gamified by **`sprint`** — a typed, tested CLI (XP, levels,
achievements, per-skill mastery) that is itself an idiomatic Python codebase the
learner reads from day one. Per-skill mastery data drives an **adaptive curriculum**:
after the fixed early modules, what gets built next is chosen from where the learner is
weakest.

This is not a "learn to program" course. Programming fundamentals are assumed. Every
module leads with *"coming from another language you'd expect X; Python does Y — and
here's why."*

## Learner profile

- Fluent in one or more other languages; writes production code daily.
- New to Python's specific syntax, idioms, standard library, and tooling.
- Values idiomatic, typed, tested code over quick hacks.
- Learns best by writing the load-bearing code themselves against a failing test.

## Goals / Non-goals

### Goals

- Idiomatic command of the core language surface: data model, comprehensions,
  generators, functions/decorators, classes/dataclasses, typing, errors.
- Working command of the workspace toolchain: `uv`, `ruff`, `pytest`, `pyproject.toml`.
- A gamified progress engine (`sprint`) that tracks XP/achievements/mastery and steers
  reinforcement.
- One packaged, typed, tested CLI capstone that combines every module.

### Non-goals (YAGNI for v1)

- Domain specializations (web frameworks, data science, ML) — deferred.
- Advanced/deep topics (asyncio, metaclasses/descriptors, performance profiling,
  C extensions, PyPI publishing) — out of the core Sprint scope; a follow-on
  "Deep-Dive" track can add them.
- Fancy UI for `sprint` (TUI, colors beyond simple ASCII, web dashboard) — plain text.
- Multi-learner support, cloud sync, auth — single local learner only.

## Learning model

**Module mechanic.** Each module is a self-contained directory with a fixed shape:

| File | Role |
| --- | --- |
| `README.md` | Concept brief: idioms, gotchas, cross-language contrasts, short annotated examples. Tight — no fundamentals. |
| `exercise.py` | Stubbed signatures + docstrings + type hints with `TODO` markers. **The learner writes the load-bearing 5–40 lines.** Never pre-filled. |
| `test_exercise.py` | A `pytest` suite that *specifies* the required behavior. |

**Session loop.** Read brief → `sprint status`/`sprint next` → run `pytest` (red) →
implement the `TODO`s → `pytest` (green) → `sprint done <mod>` (awards XP, updates
mastery, unlocks badges) → request review → reviewer critiques for *idiom and style* →
`sprint review <mod> --score N`. `ruff` runs throughout; `mypy` from Module 06.

**Contribution contract (learning mode).** Scaffolding (signatures, docstrings, tests,
READMEs) and the `sprint` engine are authored for the learner; the **load-bearing
implementation in `exercise.py` is NEVER pre-filled**. Reference answers are revealed
(and peek-recorded) via `sprint reveal <mod>`.

## Toolchain

Grounded in this workspace's Python standards (`.ai/context/python-standards.md`):

- **Python**: pinned via `.python-version` (target 3.12+; exact pin set in Module 00).
- **Environment / packaging**: `uv`, `pyproject.toml`. The project **is** an installable
  package (uv_build backend) so `sprint` is a real console script; module/solution dirs
  are excluded from the wheel.
- **Format + lint**: `ruff format`, `ruff check` (line length 88).
- **Types**: type hints on all public signatures; `mypy` from Module 06 (and on the
  `sprint` engine from the start).
- **Tests**: `pytest`, Arrange-Act-Assert.

## Directory structure

```text
learning/python/
├── README.md              # curriculum overview, setup, the loop
├── pyproject.toml         # uv + uv_build; ruff/pytest/mypy config; sprint entry point
├── .python-version        # pinned interpreter
├── src/sprint/            # the gamified progress engine (installed console script)
│   ├── __init__.py
│   ├── catalog.py         # data-driven module list + skill tags + XP weights
│   ├── models.py          # dataclasses: Ledger, ModuleRecord, SkillMastery, Achievement
│   ├── store.py           # atomic JSON load/save of the ledger
│   ├── scoring.py         # XP formula, levels, combo, mastery updates
│   ├── achievements.py    # curated badge defs + unlock predicates
│   ├── render.py          # pure ledger→string rendering
│   └── cli.py             # argparse subcommands
├── tests/                 # pytest suite for the sprint engine
├── modules/
│   ├── 00-setup/          # README + check.py (stub) + test_check.py
│   └── 01-data-model/     # README + exercise.py (stub) + test_exercise.py
├── capstone/              # spec + the learner's build (authored at Module 07)
├── solutions/             # reference idiomatic answers (revealed via `sprint reveal`)
└── .sprint/ledger.json    # runtime progress state (git-ignored)
```

## Gamification subsystem (`sprint`)

**Architecture.** Small, typed, tested package; each file has one responsibility
(`catalog`/`models`/`store`/`scoring`/`achievements`/`render`/`cli`). `cli.py` is a thin
argparse wrapper over pure logic so the engine is unit-testable. The ledger persists to
`.sprint/ledger.json` via an atomic write (temp file + replace).

**Data-driven catalog.** `catalog.py` lists every module with its skill tags and XP
weight and a `built` flag. Only `00`/`01` start `built`; the rest render as
locked/planned until generated. Adding a module later is one catalog entry — this is
how the dynamic cadence stays decoupled from the engine.

**Scoring (quality + arcade).**

| Source | XP |
| --- | --- |
| Module base | +100 (capstone +300) |
| No-peek clear | +40 |
| Ruff-clean on first submit | +20 |
| Idiomatic-review score (assigned 0–3) | +20 each → up to +60 |
| Combo (consecutive no-peek clears) | multiplies the run's *bonus* by `1 + 0.1×(combo−1)`, capped ×1.5 |
| Streak (active days) | +10 on first action each day, capped |

**Levels.** Novice (0) → Apprentice (150) → Journeyman (400) → Pythonista (800) →
Core Dev (1300) → Maintainer (1800).

**Per-skill mastery → reinforcement.** Each module tags skills (e.g. M01 →
`data-model`, `equality`, `hashing`, `truthiness`, `mutable-defaults`). Clearing a
module raises those skills' mastery (weighted by no-peek/review); peeks and retries
dampen it. `sprint next` recommends the lowest-mastery built skill — the signal that
picks the next/reinforcement module.

**Peek mechanic.** The sanctioned way to view a reference answer is `sprint reveal
<mod>`, which prints it and records a peek (self-recording honor system).

**CLI surface.**

| Command | Does |
| --- | --- |
| `sprint status` | dashboard: level bar, module progress, streak, recent, next |
| `sprint done <mod>` | runs the module's tests + ruff; on green awards XP, updates combo/mastery, unlocks badges, prints deltas; refuses if red |
| `sprint reveal <mod>` | prints the reference solution; records a peek |
| `sprint review <mod> --score N` | records the idiomatic-review score (0–3) |
| `sprint skills` / `sprint achievements` / `sprint next` | mastery meters / badges / recommendation |

**Curated badges.** First Green · No-Peek Novice · Ruff Rider (3 clean first-submits) ·
Combo Breaker (×3 no-peek combo) · Generator Guru (clear M04) · Type Wrangler (M06
mypy-clean) · Test Pilot (clear M07) · Streak Week (7-day streak) · Centurion (1000 XP)
· Capstone Champion (ship it).

**Testability note.** Streak/level/mastery functions take an optional injected `today`
(`date | None`) and operate on explicit inputs — no hidden globals — so the engine's
own test suite is deterministic (and models a good idiom for the learner).

## Module breakdown

Only Modules 00–01 are built up front. Modules 02–07 are **generated on demand**, their
order chosen adaptively by `sprint next` from per-skill mastery. The table is the
planned surface; each entry firms up at authoring time.

| # | Module | Learner writes | Key idioms / gotchas |
| --- | --- | --- | --- |
| 00 | **Setup** | `check.py` smoke test | uv, venv, ruff, pytest, pyproject; pin the interpreter |
| 01 | **Data model** | a value type (`__eq__`/`__repr__`/`__hash__`/`__bool__`) | names-vs-values, `is` vs `==`, truthiness, **mutable default-arg trap** |
| 02 | **Data structures** | a parse-and-group transform | comprehensions, unpacking, slicing, `Counter`/`defaultdict` |
| 03 | **Functions** | a `@retry`/`@timed` decorator | `*args`/`**kwargs`, keyword-only, closures, `functools` |
| 04 | **Iterators & generators** | a lazy streaming pipeline | `yield`, generator exprs, `itertools`, verified laziness |
| 05 | **Classes Pythonically** | a context manager + a protocol | `@dataclass`, properties, `__enter__`/`__exit__`, duck typing |
| 06 | **Typing & errors** | harden an untyped module to mypy-clean | `Protocol`/`TypedDict`, PEP 604 unions, EAFP, custom exceptions |
| 07 | **Testing & packaging** | tests + a console entry point | fixtures, `parametrize`, `tmp_path`, `src/` layout, `console_scripts` |

## Capstone

One **typed, tested, packaged CLI** combining every module — default a structured-log /
CSV analyzer, finalized at Module 07 so it can track the learner's real interests. Its
spec is written into `capstone/README.md` at that point.

## Resolved decisions

- **Cadence — fully dynamic.** Only the skeleton, the `sprint` engine, Module 00, and
  Module 01 are built up front. Every later module is generated on demand, its subject
  and order chosen by `sprint next` from mastery data. No fixed backlog.
- **Progress tracking — `sprint` CLI** over a git-ignored JSON ledger (installed console
  script; dogfoods the curriculum).
- **Scoring — quality + arcade**: base + no-peek/ruff-clean/review bonuses, combo
  multiplier, daily streak, per-skill mastery.
- **Achievements — curated set** (above), tweakable.
- **Reference solutions — reveal-gated**: shown via `sprint reveal`, which records a peek.

## Success criteria

- The `sprint` engine's own `tests/` suite passes; `ruff` and `mypy --strict` are clean
  on `src/sprint/`.
- `uv run sprint status` renders; `sprint done` awards XP only on green tests; badges and
  levels unlock at the defined thresholds.
- Each module's `test_exercise.py` passes with the learner's own implementation, and
  `sprint done <mod>` records it.
- The capstone installs and runs via `uv run`, its suite passes, and it uses constructs
  from every module.

## First increment (for the implementation plan)

1. `learning/python/` skeleton: `pyproject.toml` (uv + uv_build + `sprint` entry point,
   ruff/pytest/mypy config), `.python-version`, root `README.md`, `.gitignore` update for
   `.sprint/`, empty `modules/` `capstone/` `solutions/`.
2. The **`sprint` engine** (`src/sprint/*` + `tests/*`), TDD, `mypy --strict` clean.
3. **Module 00 (Setup)** fully: `README.md` + `check.py` (stub) + `test_check.py` +
   `solutions/00-setup.py`; catalog entry `built`.
4. **Module 01 (Data model)** fully: `README.md` + `exercise.py` (stub) +
   `test_exercise.py` + `solutions/01-data-model.py`; catalog entry `built`.

## Deferred / open

- Modules 02–07 subjects/order — chosen dynamically at authoring time from mastery data.
- Exact capstone subject — finalized at Module 07.
- Optional follow-on "Deep-Dive" track — out of scope for this spec.
