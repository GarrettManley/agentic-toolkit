# Codex 02 — Data structures

> Cleared 2026-08-17 · reviewed **1/3** · stats: `comprehensions`, `collections`,
> `unpacking`
>
> Reinforced by **Module 02b** (codex entry sealed until that dungeon falls).

## The one-line version

This is the **accent module**: every exercise has a working non-Python solution you
already know how to write, all of them pass the tests, and none of them read as
Python. Comprehensions replace accumulator loops, `collections` replaces the
structure you were about to hand-roll, and unpacking replaces indexing.

## Concepts

### Comprehensions replace the accumulator loop

```python
result = []                       →    [f(x) for x in xs if cond]
for x in xs:
    if cond:
        result.append(f(x))
```

One expression, so it can be returned directly, with no mutable temporary to get
wrong. Four forms: `list` `[...]`, `set` `{x ...}`, `dict` `{k: v ...}`, and
generator `(...)` — the last is lazy and is what you want inside `sum()`, `join()`,
`any()`, or `next()`.

Do **not** reach for `map`/`filter` with a `lambda`. A comprehension is the idiomatic
form for both.

### Unpack in the `for` clause

`for name, item, gold in rows` — not `row[0]`, `row[1]`, `row[2]`. Positional indexing
into a tuple whose columns have meanings is a code smell; the names document the data.

### `enumerate` and `zip`, never `range(len(...))`

`enumerate(xs, start=1)` yields `(index, value)` and takes a start, so you never write
`i + 1`. `zip(a, b)` walks two sequences in lockstep. Manual index arithmetic is the
loudest transplant accent in Python.

### `collections` has the structure you were about to build

| You were about to write | Reach for |
|---|---|
| `if k not in d: d[k] = 0` then `d[k] += n` | `Counter` or `defaultdict(int)` |
| `if k not in d: d[k] = []` then `d[k].append(x)` | `defaultdict(list)` or `dict.setdefault` |
| sort a tally and slice the top N | `Counter(...).most_common(n)` |
| `list.pop(0)` in a loop | `deque` (O(1) both ends) |

**Trust the container to be the result, not a helper toward it.** `Counter` *is* a
`dict` subclass — `dict(counter)` is the whole answer, not the start of one.

### The `defaultdict` leak

Every lookup of a missing key **inserts** that key. A `defaultdict` returned to a
caller silently grows as it is *read*. Build with it, return `dict(d)`.

### Starred targets and starred parameters

Two faces of the same feature:

```python
head, *body, tail = seq          # assignment: *body is a LIST of the leftovers
def f(a, *args, **kwargs): ...   # signature: *args is a TUPLE, **kwargs a dict
```

The star may sit anywhere in an assignment's target list. In a signature, `*`
collects extra positionals and `**` collects keywords (insertion-ordered).

### Merging mappings without mutating

`{**a, **b}` and `a | b` both build a **new** dict where later keys win.
`a.update(b)` and `a |= b` mutate in place — correct when you own `a`, a bug when it
came from your caller. Note that `x = x | y` in a loop reallocates every iteration;
`x |= y` on a local you own is the O(n) version.

### `ruff check` ≠ `ruff format`

`check` audits **lint** rules (unsorted imports, unused variables, `B905`).
`format` owns **layout** (blank lines, quotes, line breaks) as Black-compatible
output. The default lint set omits the blank-line rules *because* the formatter owns
them — so `check` passing does not mean the file is formatted. Run both.

## What you actually hit

- **A manual accumulator with `entry[2]` / `entry[1]`** in `high_value_items` — the
  module's headline idiom, missed twice over (no comprehension, no unpacking) — while
  `loot_by_adventurer` three functions later unpacked correctly in its `for` clause.
- **`dict[str, int]()` used as a constructor**, three times. It works: `dict[str, int]`
  is a [`types.GenericAlias`](https://docs.python.org/3/library/stdtypes.html#types-genericalias)
  whose `__call__` forwards to `dict` and **discards the parameters**. But it reads as
  `new Dictionary<string, int>()`. In Python the type lives in the *annotation*:
  `results: dict[str, int] = {}`.
- **Mirroring a `Counter` into a second dict** — the `Counter` already was the answer.
- **`inventory = inventory | inv` in a loop** — correct and non-mutating, but
  allocates a new dict per iteration. `|=` on a local you own is free.

## Reference

| Topic | Docs |
|---|---|
| List comprehensions (tutorial) | [tutorial/datastructures.html#list-comprehensions](https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions) |
| Nested comprehensions | [#nested-list-comprehensions](https://docs.python.org/3/tutorial/datastructures.html#nested-list-comprehensions) |
| Dict comprehensions | [tutorial/datastructures.html#dictionaries](https://docs.python.org/3/tutorial/datastructures.html#dictionaries) |
| Comprehension grammar (all four forms) | [expressions.html#displays…](https://docs.python.org/3/reference/expressions.html#displays-for-lists-sets-and-dictionaries) |
| `enumerate` | [functions.html#enumerate](https://docs.python.org/3/library/functions.html#enumerate) |
| `zip` | [functions.html#zip](https://docs.python.org/3/library/functions.html#zip) |
| `collections.Counter` | [collections.Counter](https://docs.python.org/3/library/collections.html#collections.Counter) |
| `collections.defaultdict` | [collections.defaultdict](https://docs.python.org/3/library/collections.html#collections.defaultdict) |
| `dict.setdefault` | [stdtypes.html#dict.setdefault](https://docs.python.org/3/library/stdtypes.html#dict.setdefault) |
| Starred assignment targets | [simple\_stmts.html#assignment-statements](https://docs.python.org/3/reference/simple_stmts.html#assignment-statements) |
| Extended iterable unpacking | [PEP 3132](https://peps.python.org/pep-3132/) |
| `*args` / `**kwargs` in signatures | [tutorial/controlflow.html#arbitrary-argument-lists](https://docs.python.org/3/tutorial/controlflow.html#arbitrary-argument-lists) |
| Unpacking at the call site | [tutorial/controlflow.html#unpacking-argument-lists](https://docs.python.org/3/tutorial/controlflow.html#unpacking-argument-lists) |
| `{**a, **b}` generalizations | [PEP 448](https://peps.python.org/pep-0448/) |
| `dict \| dict` union operator | [PEP 584](https://peps.python.org/pep-0584/) |
| `list[int]` as an annotation | [PEP 585](https://peps.python.org/pep-0585/) |
