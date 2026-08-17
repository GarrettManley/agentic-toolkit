---
date: 2026-08-17
status: approved
topic: learning/python tutorial
audience: experienced developer new to Python
---

# Python Fluency Sprint — Design Spec

## Purpose

A self-paced, test-driven tutorial that takes an **experienced developer who is new
to Python** to **idiomatic fluency** — the ability to write Python a Pythonista would
recognize as idiomatic, not merely working. It is deliberately breadth-first across
Python's data model, idioms, typing, testing, and packaging, converging into one real
capstone build.

This is not a "learn to program" course. Programming fundamentals (variables, loops,
functions-as-concept) are assumed. Every module leads with *"coming from another
language you'd expect X; Python does Y — and here's why."*

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
- One packaged, typed, tested CLI capstone that combines every module.

### Non-goals (YAGNI for v1)

- Domain specializations (web frameworks, data science, ML) — deferred; the general
  fluency track makes any of them reachable afterward.
- Advanced/deep topics (asyncio, metaclasses/descriptors, performance profiling,
  C extensions, publishing to PyPI) — explicitly out of the ~8-module Sprint scope.
  A follow-on "Deep-Dive" track can add them later.

## Learning model

**Module mechanic.** Each module is a self-contained directory with a fixed shape so
the session rhythm never changes:

| File | Role |
| --- | --- |
| `README.md` | Concept brief: idioms, gotchas, cross-language contrasts, short annotated examples. Tight — no fundamentals. |
| `exercise.py` | Stubbed signatures + docstrings + type hints with `TODO` markers. **The learner writes the load-bearing 5–40 lines.** Never pre-filled. |
| `test_exercise.py` | A `pytest` suite that *specifies* the required behavior. |

**Session loop.** Read brief → run `pytest` (red) → implement the `TODO`s → run
`pytest` (green) → request review → reviewer critiques for *idiom and style*, not just
correctness → diff against the reference solution. `ruff format` + `ruff check` run
throughout; `mypy` joins from Module 06 onward.

**Contribution contract (learning mode).** The tutorial author scaffolds signatures,
docstrings, and tests — but never the meaningful implementation. The learner writes
the code that shapes behavior; that is the point of the exercise.

## Toolchain

Grounded in this workspace's Python standards (`.ai/context/python-standards.md`):

- **Python**: pinned via `.python-version` (target 3.12+; exact pin decided in Module 00
  against what is installed).
- **Environment / packaging**: `uv`, `pyproject.toml`.
- **Format + lint**: `ruff format`, `ruff check` (line length 88).
- **Types**: type hints on all public signatures; `mypy` from Module 06.
- **Tests**: `pytest`, Arrange-Act-Assert.

## Directory structure

```text
learning/python/
├── README.md              # curriculum overview, setup, progress tracker
├── pyproject.toml         # uv-managed; ruff + pytest config
├── .python-version        # pinned interpreter
├── modules/
│   ├── 00-setup/          # env bootstrap + check.py smoke test
│   ├── 01-data-model/     # README.md + exercise.py + test_exercise.py
│   ├── 02-data-structures/
│   ├── 03-functions/
│   ├── 04-iterators-generators/
│   ├── 05-classes/
│   ├── 06-typing-errors/
│   └── 07-testing-packaging/
├── capstone/              # spec + the learner's build (final sessions)
└── solutions/             # reference idiomatic solutions (attempt-first)
```

## Module breakdown

| # | Module | Learner writes | Key idioms / gotchas |
| --- | --- | --- | --- |
| 00 | **Setup** | `check.py` smoke test | uv, venv, ruff, pytest, pyproject; why the tooling; pin the interpreter |
| 01 | **Data model** | a value type (`__eq__`/`__repr__`/`__hash__`) | names-vs-values, `is` vs `==`, truthiness, **mutable default-arg trap**, dunders |
| 02 | **Data structures** | a parse-and-group transform | comprehensions (list/dict/set/gen), unpacking, slicing, `enumerate`/`zip`, `Counter`/`defaultdict` |
| 03 | **Functions** | a `@retry` or `@timed` decorator | `*args`/`**kwargs`, keyword-only args, closures, `functools` (`wraps`, `partial`, `lru_cache`) |
| 04 | **Iterators & generators** | a lazy streaming pipeline | iterator protocol, `yield`, generator expressions, `itertools`, verified laziness |
| 05 | **Classes Pythonically** | a context manager + a protocol-based design | `@dataclass` (frozen/slots), properties, `__enter__`/`__exit__`, duck typing, `__iter__` |
| 06 | **Typing & errors** | harden an untyped module to mypy-clean | `Protocol`/`TypedDict`, `Optional`, PEP 604 unions, EAFP vs LBYL, custom exceptions, `try/except/else/finally` |
| 07 | **Testing & packaging** | tests + a console entry point | `pytest` fixtures, `parametrize`, `tmp_path`, `monkeypatch`, `src/` layout, `console_scripts` |

## Capstone

One **typed, tested, packaged CLI tool** that forces every module together. Default
proposal: a **structured-log / CSV analyzer** — streams input (generators), parses into
dataclasses (classes + typing), transforms (comprehensions + `functools`), exposes
subcommands (argparse), does file I/O via context managers, raises custom exceptions,
ships a full `pytest` suite, and installs as `uv run <tool>`. Deterministic input keeps
it cleanly testable.

The capstone's exact subject is **finalized at Module 07**, so it can be swapped for
something closer to the learner's real automation work if preferred. The capstone spec
in `capstone/README.md` is written at that point.

## Resolved decisions

- **Build cadence — just-in-time.** The skeleton, Module 00, and Module 01 are built
  first. Each later module is generated when the learner reaches it, so content adapts
  to where they actually struggle or pivot (rather than a fixed up-front dump). The
  implementation plan reflects this: one phase per module, executed on demand.
- **Reference solutions — present, attempt-first.** A `solutions/` directory ships
  from the start with an explicit *"attempt the exercise before opening this"* note in
  the root README. Trivial to switch to on-request delivery later if it proves tempting.

## Success criteria

- Each module's `test_exercise.py` passes with the learner's own implementation.
- `ruff check` and `ruff format --check` are clean across `learning/python/`.
- From Module 06 on, `mypy` is clean on the modules that ship type hints.
- The capstone installs and runs via `uv run`, its test suite passes, and it
  demonstrably uses constructs from every module.

## First increment (for the implementation plan)

The `writing-plans` step should produce a plan whose first executable phase scaffolds:

1. `learning/python/` skeleton: root `README.md` (overview + how-to + progress tracker),
   `pyproject.toml` (uv + ruff + pytest config), `.python-version`, empty `modules/`,
   `capstone/`, `solutions/`.
2. **Module 00 (Setup)** fully: `README.md` + `check.py` + a trivial passing test that
   proves the red/green loop works end to end.
3. **Module 01 (Data model)** fully: `README.md` + `exercise.py` (stubbed) +
   `test_exercise.py` + `solutions/01-data-model.py`.

Modules 02–07 and the capstone are subsequent phases, each executed just-in-time.

## Deferred / open

- Exact capstone subject — finalized at Module 07.
- Optional follow-on "Deep-Dive" track (async, metaprogramming, performance,
  publishing) — out of scope for this spec.
