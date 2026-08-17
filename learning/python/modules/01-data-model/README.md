# Module 01 — Python's data model

Python has no "primitives vs objects" split: **everything is an object**, and the
language's behaviour is defined by *dunder* (double-underscore) methods you implement
yourself. This module makes a `Money` value type behave correctly under `repr()`,
`==`, `hash()`, and `bool()`.

## Coming from another language

- **Names are not variables.** A name is a label bound to an object. `a = b` binds the
  same object to two names; it does not copy. `is` compares identity (same object);
  `==` compares value (via `__eq__`). Reach for `==` by default.
- **Equality is opt-in.** By default `==` falls back to identity. You get value
  equality by writing `__eq__` — and then you **must** write `__hash__` too, or the
  class becomes unhashable (unusable as a `set` member or `dict` key).
- **Return `NotImplemented`, don't raise.** When `__eq__` gets an operand it doesn't
  understand, returning the special `NotImplemented` singleton lets Python try the
  other operand's comparison before falling back to `is`. Returning `False` would lie;
  raising would break `!=` and containment checks.
- **Truthiness is customisable.** `if money:` calls `__bool__`. Empty/zero things are
  conventionally falsy (`[]`, `0`, `""`, `None`).
- **The mutable default trap.** `def f(x, acc=[])` creates the list *once*, at
  definition time, and reuses it on every call — state leaks between calls. The idiom
  is `acc: list | None = None` then `if acc is None: acc = []`.

## Your task

Implement the four `TODO`s in `exercise.py` (`__repr__`, `__eq__`, `__hash__`,
`__bool__`) and the `running_total` function, then make
`uv run pytest modules/01-data-model -v` go green. When done:
`uv run sprint done 01`, then ask for a review.

Note for later: Module 05 shows `@dataclass` *generating* `__init__`/`__repr__`/`__eq__`
/`__hash__` for you. Writing them by hand here is what makes that shortcut make sense.
