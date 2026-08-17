# Python Fluency Sprint

A self-paced, test-driven path from *experienced developer* to *idiomatic Python* —
breadth-first across Python's data model, idioms, typing, testing, and packaging,
converging on one real capstone CLI. Progress is gamified by **`sprint`** (XP, levels,
achievements, per-skill mastery).

Not a "learn to program" course — fundamentals are assumed. Each module leads with
*"coming from another language you'd expect X; Python does Y — and here's why."*

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) installed (`uv --version`).
- Python 3.12+ (uv fetches the pinned version from `.python-version` automatically).

## Setup

```bash
cd learning/python
uv sync                     # create .venv, install the sprint tool + dev deps
uv run sprint status        # your dashboard (starts at Level 1 · Novice)
uv run pytest modules/00-setup -v
```

## How a module works

Each `modules/NN-name/` directory has:

| File | What it is |
| --- | --- |
| `README.md` | The concept brief: idioms, gotchas, cross-language contrasts. |
| `exercise.py` | Stubbed signatures with `TODO`s. **You write the real code here.** |
| `test_exercise.py` | The behavior spec. Make it pass. |

## The loop (every module)

1. Read the module `README.md`; check `uv run sprint next` for what to tackle.
2. `uv run pytest modules/NN-name -v` → **red**.
3. Implement the `TODO`s in `exercise.py`.
4. `uv run pytest modules/NN-name -v` → **green**.
5. `uv run sprint done NN` → awards XP, updates mastery, unlocks achievements.
6. Ask for a review — the goal is *idiomatic*, not merely *passing* — then
   `uv run sprint review NN --score <0-3>`.

> Run one module at a time. To run everything at once:
> `uv run pytest modules --import-mode=importlib`.

## The `sprint` tool

| Command | Does |
| --- | --- |
| `sprint status` | dashboard: level bar, module progress, streak, recent, next |
| `sprint done NN` | run a module's tests + ruff; on green, award XP and update everything |
| `sprint reveal NN` | show the reference solution (records a peek — no shame, just data) |
| `sprint review NN --score N` | record the idiomatic-review score (0–3) |
| `sprint skills` | per-skill mastery meters |
| `sprint achievements` | badges earned and still locked |
| `sprint next` | what to do (or reinforce) next |

`sprint` is a real, typed, tested Python package under `src/sprint/` — read it; it's an
idiomatic example of the very things you're learning.

## Solutions

`solutions/NN-name.py` holds a reference answer for each module. **Attempt the exercise
first** — reveal it through `sprint reveal NN` (which records the peek) only after your
tests pass or you're truly stuck. There's usually more than one idiomatic answer.
