# Codex 01 — Python's data model

> Cleared 2026-08-17 · reviewed **3/3** · stats: `data-model`, `equality`, `hashing`,
> `truthiness`, `mutable-defaults`

## The one-line version

Python's behaviour is defined by **dunder methods you implement**, the interpreter
calls them on your behalf via builtins and operators, and `__eq__`/`__hash__` are a
contract rather than two independent methods.

## Concepts

### Dunders are hooks, not an API

The `__name__` namespace is reserved by the language — never invent your own. You
implement them; the interpreter calls them. `hash(x)` **is**
`type(x).__hash__(x)`; `a == b` **is** `a.__eq__(b)`; `if x:` **is** `x.__bool__()`.

**Always call the builtin, never the dunder.** `hash()` truncates the return value to
`Py_hash_t` and remaps the `-1` error sentinel to `-2`; `==` handles the
`NotImplemented` reflection dance. Reaching past the builtin skips all of it.

### Special-method lookup skips the instance

For implicit invocations, Python looks the dunder up on the **type**, not the object.
Assigning `obj.__len__ = f` will not change what `len(obj)` does. This is why dunders
live on the class.

### The `__eq__` / `__hash__` contract

> Equal objects **must** hash equal. Unequal objects **may** also hash equal.

That asymmetry is the whole design. A hash is a lossy projection onto a fixed-width
integer, so collisions are arithmetic, not defects. `dict` hashes to find a bucket,
then calls `__eq__` to resolve collisions *within* it. Equality is ground truth; hash
is the fast index built from it — never the reverse.

Define `__eq__` without `__hash__` and Python makes the class **unhashable
automatically**. That's the interpreter refusing to let you ship a broken invariant.

The idiomatic implementation of both is a tuple of the same fields:
`hash((self.a, self.b))` — order-sensitive, avalanching, and exactly what
`@dataclass(frozen=True)` generates.

### `NotImplemented` vs `NotImplementedError`

Near-identical names, unrelated mechanics.

| | What it is | What you do with it | Meaning |
|---|---|---|---|
| `NotImplemented` | a singleton **value** | `return` it | "I don't handle this type — you try" |
| `NotImplementedError` | an **exception** | `raise` it | "this method is a stub" |

Returning `NotImplemented` from `__eq__` lets Python try `other.__eq__(self)`, then
fall back to identity. Returning `False` asserts definitive inequality and shuts down
any future type that knows how to compare itself to yours.

### The underscore taxonomy

| Spelling | Meaning | Enforced? |
|---|---|---|
| `name` | public | — |
| `_name` | internal by convention | only affects `from m import *` |
| `__name` | **name mangling** → `_Class__name` | yes, by the compiler |
| `name_` | dodge a keyword collision (`class_`) | — |
| `__name__` | reserved dunder (exempt from mangling) | yes, by the interpreter |

Name mangling is **collision avoidance for subclassing, not privacy** — `obj._Class__x`
works fine from outside. Use `_single` for "internal"; `__double` is rare and correct
mostly in base classes meant for strangers to subclass.

### Truthiness

`if x:` calls `__bool__`, falling back to `__len__`, falling back to "always true".
Empty/zero things are conventionally falsy: `0`, `""`, `[]`, `{}`, `None`.

### The mutable default trap

Default arguments are evaluated **once, at function-definition time**, and stored on
the function object (`f.__defaults__`). A `def f(x, acc=[])` shares one list across
every call for the life of the process.

There is no per-call default mechanism, so the fix is a sentinel:

```python
def f(x, acc=None):
    if acc is None:
        acc = []      # the guard's ONLY job
    acc.append(x)     # the work, once, unconditional
    return acc
```

The guard normalizes the input and does nothing else. If both branches of an
`if/else` carry business logic, that's a branch, not the sentinel idiom.

Use `is None`, never `== None` — `None` is a singleton, identity can't be intercepted,
and `==` dispatches to `__eq__` (numpy returns an array from `== None` and then
explodes in the `if`). When `None` is itself a legal value, use a private sentinel:
`_MISSING = object()`.

## What you actually hit

- **`return hash(self)` inside `__hash__`** → `RecursionError`. `hash()` is the front
  door to the method you're standing in, not a smarter separate function.
- **`self.__hash__ == other.__hash__`** compared two *bound method objects*, not
  hashes — always `False` for distinct instances (CPython compares `im_self` by
  identity), so it was dead code that looked load-bearing.
- **`__eq__` returning hash equality** promoted every collision into a false equality.
  Live counterexample: `hash(2**61 - 1) == 0`, so `Money(0)` compared equal to
  `Money(2305843009213693951)` and a `set` of both had one element.
- **`hash(a) + hash(b)`** is commutative and cheap to collide. `hash((a, b))` uses
  CPython's xxPRIME-based tuple algorithm instead.

## Reference

| Topic | Docs |
|---|---|
| The data model (all dunders) | [reference/datamodel.html](https://docs.python.org/3/reference/datamodel.html) |
| `__repr__` | [object.\_\_repr\_\_](https://docs.python.org/3/reference/datamodel.html#object.__repr__) |
| `__eq__` | [object.\_\_eq\_\_](https://docs.python.org/3/reference/datamodel.html#object.__eq__) |
| `__hash__` (incl. the contract) | [object.\_\_hash\_\_](https://docs.python.org/3/reference/datamodel.html#object.__hash__) |
| `__bool__` | [object.\_\_bool\_\_](https://docs.python.org/3/reference/datamodel.html#object.__bool__) |
| Special method lookup skips instances | [reference/datamodel.html#special-lookup](https://docs.python.org/3/reference/datamodel.html#special-lookup) |
| `hash()` builtin | [functions.html#hash](https://docs.python.org/3/library/functions.html#hash) |
| `NotImplemented` | [constants.html#NotImplemented](https://docs.python.org/3/library/constants.html#NotImplemented) |
| `NotImplementedError` | [exceptions.html#NotImplementedError](https://docs.python.org/3/library/exceptions.html#NotImplementedError) |
| Truth value testing | [stdtypes.html#truth-value-testing](https://docs.python.org/3/library/stdtypes.html#truth-value-testing) |
| Name mangling / private variables | [tutorial/classes.html#private-variables](https://docs.python.org/3/tutorial/classes.html#private-variables) |
| **Why default values are shared** | [faq/programming.html](https://docs.python.org/3/faq/programming.html#why-are-default-values-shared-between-objects) |
| Default argument values | [tutorial/controlflow.html#default-argument-values](https://docs.python.org/3/tutorial/controlflow.html#default-argument-values) |
| f-strings | [lexical\_analysis.html#f-strings](https://docs.python.org/3/reference/lexical_analysis.html#f-strings) |
| `!r` and format specs | [string.html#format-string-syntax](https://docs.python.org/3/library/string.html#format-string-syntax) |
| `dataclasses.field(default_factory=…)` | [dataclasses.field](https://docs.python.org/3/library/dataclasses.html#dataclasses.field) |
