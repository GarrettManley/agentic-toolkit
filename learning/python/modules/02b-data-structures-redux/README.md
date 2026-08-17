# Module 02b — Data structures, reforged

Your character sheet reads **50%** on `comprehensions`, `collections`, and
`unpacking`. Not because you don't know them — Module 02 proved you do — but
because they aren't reflexive yet. This dungeon drills the same three stats on
harder targets.

**The docstrings do not name the technique this time.** Each states a contract and
an example. Working out *which* tool applies is the exercise now.

## What's new here

Module 02 covered the basic shapes. These are the ones that separate "I can write a
comprehension" from "I reach for the right one without thinking":

- **Nested comprehensions.** Two `for` clauses in one comprehension read
  **left-to-right, outer-to-inner** — the same order as the nested loops they
  replace. This trips almost everyone the first time.
- **Filter vs. transform.** `[f(x) for x in xs if cond]` *drops* elements;
  `[a if cond else b for x in xs]` *keeps every element* and changes the value. Same
  keyword, two positions, completely different result — note where the `if` sits.
- **`zip` truncates silently.** It stops at the shortest input. That's usually what
  you want and occasionally a bug; `zip(a, b, strict=True)` (3.10+) raises instead.
  This project enables ruff's `B905`, which **rejects a bare `zip()`** — you have to
  write `strict=True` or `strict=False` and say which behaviour you meant. Read the
  contract in the docstring before you pick.
- **`Counter` does the ranking too.** `most_common(n)` is already sorted, already
  bounded, and already returns `(item, count)` pairs.
- **`*args` / `**kwargs` in a signature** are the mirror of starred unpacking in an
  assignment: `*` collects extra positionals into a **tuple**, `**` collects keywords
  into a **dict** (insertion-ordered).
- **`str.join` + a generator expression** is the idiomatic way to build a delimited
  string. And `", ".join(xs) or "fallback"` leans on the empty string being falsy.

## The trap

One of the seven is **not** a comprehension problem. If a result's element *i*
depends on element *i-1*, no comprehension can express it cleanly — that's a fold,
not a map. Recognising when to *not* reach for the shiny tool is as much a fluency
signal as reaching for it. `itertools` has the clean answer; a plain loop is the
honest fallback and scores fine.

## Your task

Seven `TODO`s in `exercise.py`, then:

```
uv run pytest modules/02b-data-structures-redux -v
uv run ruff check modules/02b-data-structures-redux
uv run ruff format --diff modules/02b-data-structures-redux
```

All three clean is the bar — `check` and `format` are different tools, and Module 02
proved it. `uv run sprint reveal 02b` shows the reference and records a peek.
