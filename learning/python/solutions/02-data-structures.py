"""Reference answer for Module 02. Attempt the exercise first."""

from __future__ import annotations

from collections import Counter, defaultdict

Entry = tuple[str, str, int]


def high_value_items(entries: list[Entry], threshold: int) -> list[str]:
    return [item for _, item, gold in entries if gold >= threshold]


def rank_table(names: list[str]) -> dict[str, int]:
    return {name: rank for rank, name in enumerate(names, start=1)}


def gold_by_adventurer(entries: list[Entry]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for name, _, gold in entries:
        totals[name] += gold
    return dict(totals)


def loot_by_adventurer(entries: list[Entry]) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for name, item, _ in entries:
        grouped[name].append(item)
    return dict(grouped)


def split_party(members: list[str]) -> tuple[str, list[str], str]:
    scout, *middle, rearguard = members
    return scout, middle, rearguard


def merge_inventories(*inventories: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for pack in inventories:
        merged |= pack
    return merged
