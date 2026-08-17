"""Module 02 -- data structures: comprehensions, collections, unpacking.

Implement each ``TODO``, then run:  uv run pytest modules/02-data-structures -v
"""

from __future__ import annotations

# An expedition ledger row: (adventurer, item, gold)
Entry = tuple[str, str, int]


def high_value_items(entries: list[Entry], threshold: int) -> list[str]:
    """Return the item names worth ``threshold`` gold or more, in ledger order.

    TODO: one list comprehension. The shape is
    ``[<expr> for <names> in <iterable> if <condition>]`` -- and because each
    entry is a 3-tuple, you can unpack it right in the ``for`` clause instead of
    indexing with ``[0]``/``[1]``/``[2]``.
    """
    raise NotImplementedError


def rank_table(names: list[str]) -> dict[str, int]:
    """Map each name to its 1-based position in ``names``.

    ``["Doran", "Mira"]`` -> ``{"Doran": 1, "Mira": 2}``

    TODO: a *dict* comprehension -- same syntax as a list comprehension but with
    ``{key: value for ...}``. Use ``enumerate`` to get positions; it takes a
    ``start=`` argument, so you never need to write ``i + 1``.
    """
    raise NotImplementedError


def gold_by_adventurer(entries: list[Entry]) -> dict[str, int]:
    """Total the gold each adventurer collected.

    TODO: accumulate a running total per name. ``collections.Counter`` and
    ``collections.defaultdict(int)`` both do this without you having to check
    whether a key exists first -- pick one and import it.

    Careful: the caller gets a plain mapping. A ``defaultdict`` handed back
    directly will silently *invent* a key the first time anyone looks one up.
    """
    raise NotImplementedError


def loot_by_adventurer(entries: list[Entry]) -> dict[str, list[str]]:
    """Group item names under the adventurer who claimed them, in ledger order.

    TODO: the group-by idiom. ``collections.defaultdict(list)`` lets you append
    without seeding the key; ``dict.setdefault`` is the stdlib-only alternative.
    Same "don't return a live defaultdict" caution as above.
    """
    raise NotImplementedError


def split_party(members: list[str]) -> tuple[str, list[str], str]:
    """Split a marching order into (scout, middle, rearguard).

    ``["Vex", "Mira", "Doran", "Kel"]`` -> ``("Vex", ["Mira", "Doran"], "Kel")``
    A two-person party has an empty middle.

    TODO: starred unpacking. ``first, *rest = seq`` binds ``rest`` to a list of
    everything left over -- and the star may sit in the middle of the targets.
    No slicing, no indexing.
    """
    raise NotImplementedError


def merge_inventories(*inventories: dict[str, int]) -> dict[str, int]:
    """Merge any number of packs into one; later packs win on conflict.

    TODO: ``*inventories`` collects the arguments into a tuple, so this must work
    for zero packs too. Build a NEW dict -- mutating ``inventories[0]`` would
    edit the caller's data. Both ``{**a, **b}`` and the ``|`` operator (3.9+)
    merge without mutating; ``functools.reduce`` is one way to fold many.
    """
    raise NotImplementedError
