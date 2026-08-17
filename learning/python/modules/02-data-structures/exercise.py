"""Module 02 -- data structures: comprehensions, collections, unpacking.

Implement each ``TODO``, then run:  uv run pytest modules/02-data-structures -v
"""

from __future__ import annotations

from collections import Counter, defaultdict

# An expedition ledger row: (adventurer, item, gold)
Entry = tuple[str, str, int]


def high_value_items(entries: list[Entry], threshold: int) -> list[str]:
    results = []
    for _, item, gold in entries:
        if gold >= threshold:
            results.append(item)
    return results


def rank_table(names: list[str]) -> dict[str, int]:
    results = dict[str, int]()

    for index, name in enumerate(names, 1):
        results[name] = index
    return results


def gold_by_adventurer(entries: list[Entry]) -> dict[str, int]:
    results = dict[str, int]()
    count = Counter()
    for adventurer, _, gold in entries:
        count[adventurer] += gold
        results[adventurer] = count[adventurer]
    return results


def loot_by_adventurer(entries: list[Entry]) -> dict[str, list[str]]:
    dictionary = defaultdict(list)
    for adventurer, item, _ in entries:
        dictionary[adventurer].append(item)
    return dict(dictionary)


def split_party(members: list[str]) -> tuple[str, list[str], str]:
    """Split a marching order into (scout, middle, rearguard).

    ``["Vex", "Mira", "Doran", "Kel"]`` -> ``("Vex", ["Mira", "Doran"], "Kel")``
    A two-person party has an empty middle.

    TODO: starred unpacking. ``first, *rest = seq`` binds ``rest`` to a list of
    everything left over -- and the star may sit in the middle of the targets.
    No slicing, no indexing.
    """
    first, *middle, last = members
    return (first, middle, last)


def merge_inventories(*inventories: dict[str, int]) -> dict[str, int]:
    """Merge any number of packs into one; later packs win on conflict.

    TODO: ``*inventories`` collects the arguments into a tuple, so this must work
    for zero packs too. Build a NEW dict -- mutating ``inventories[0]`` would
    edit the caller's data. Both ``{**a, **b}`` and the ``|`` operator (3.9+)
    merge without mutating; ``functools.reduce`` is one way to fold many.
    """
    inventory = dict[str, int]()
    for inv in inventories:
        inventory = inventory | inv
    return inventory
