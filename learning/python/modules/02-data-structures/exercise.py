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
    first, *middle, last = members
    return (first, middle, last)


def merge_inventories(*inventories: dict[str, int]) -> dict[str, int]:
    inventory = dict[str, int]()
    for inv in inventories:
        inventory = inventory | inv
    return inventory
