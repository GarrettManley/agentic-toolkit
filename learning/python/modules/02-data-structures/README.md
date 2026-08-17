# Module 02 — Data structures

Comprehensions, `collections`, and unpacking. This is the highest-density idiom cluster
in the language: it is where Python code stops looking like C or Java with different
punctuation and starts looking like Python. You will build a small expedition ledger —
a list of `(adventurer, item, gold)` rows — and answer questions about it.

## Coming from another language

- **Comprehensions replace the accumulator loop.** The pattern
  `result = []` / `for x in xs:` / `if cond:` / `result.append(f(x))` collapses to
  `[f(x) for x in xs if cond]`. It reads in the same order you'd say it aloud, and it
  is one expression, so it can be returned directly. There are `list`, `dict`
  (`{k: v for ...}`), `set` (`{x for ...}`), and generator (`(x for ...)`) forms.
  Do **not** reach for `map`/`filter` with a `lambda` — a comprehension is the
  idiomatic form for both.
- **Unpack in the `for` clause.** Iterating tuples? Write `for name, item, gold in rows`
  rather than `row[0]`, `row[1]`, `row[2]`. Positional indexing into a tuple is a code
  smell in Python; the names document what the columns mean.
- **`enumerate` and `zip`, never `range(len(...))`.** `enumerate(xs)` yields
  `(index, value)` pairs and takes a `start=` argument. `zip(a, b)` walks two sequences
  in lockstep. Indexing by hand is the loudest transplant accent there is.
- **`collections` has the data structure you were about to hand-roll.**
  `Counter` tallies (`Counter(words).most_common(3)`); `defaultdict(list)` lets you
  `d[key].append(x)` without seeding the key first; `deque` is an O(1)-both-ends queue.
  Reaching for `if key not in d: d[key] = []` means you haven't met them yet.
- **Starred targets absorb the leftovers.** `first, *rest = seq` binds `rest` to a
  *list* of everything remaining, and the star may sit anywhere in the target list
  (`head, *body, tail = seq`). In a function signature, `*args` collects positional
  arguments into a tuple and `**kwargs` collects keyword arguments into a dict.
- **`**` and `|` merge mappings without mutating.** `{**a, **b}` and `a | b` both build
  a *new* dict where later keys win. `a.update(b)` mutates `a` in place — fine when you
  own `a`, a bug when it came from your caller.

## The gotcha this module tests

`defaultdict` is a great *builder* and a leaky *return value*. Every lookup of a missing
key **inserts** that key, so a `defaultdict` handed back to a caller quietly grows as it
is read. Build with it, then return `dict(d)`.

## Your task

Implement the six `TODO`s in `exercise.py`, then:

```
uv run pytest modules/02-data-structures -v
uv run ruff check modules/02-data-structures
```

Green plus ruff-clean is the bar. `uv run sprint reveal 02` shows the reference answer
and records a peek — your call, your XP.
