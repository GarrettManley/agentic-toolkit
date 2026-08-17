"""Reference answer for Module 02b. Attempt the exercise first."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import accumulate


def flatten_hauls(hauls: dict[str, list[str]]) -> list[str]:
    return [item for pack in hauls.values() for item in pack]


def label_hauls(golds: list[int], threshold: int) -> list[str]:
    return ["rich" if gold >= threshold else "meager" for gold in golds]


def assign_mounts(riders: list[str], mounts: list[str]) -> dict[str, str]:
    # strict=False is the point: the contract says drop the unmatched tail.
    # ruff's B905 refuses to let the choice stay implicit.
    return dict(zip(riders, mounts, strict=False))


def top_items(items: list[str], n: int) -> list[tuple[str, int]]:
    return Counter(items).most_common(n)


def by_rarity(catalogue: dict[str, str]) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for item, rarity in catalogue.items():
        grouped[rarity].append(item)
    return dict(grouped)


def party_sheet(leader: str, *members: str, **gear: int) -> str:
    company = ", ".join(members) or "nobody"
    packs = ", ".join(f"{item} x{count}" for item, count in gear.items()) or "nothing"
    return f"{leader} leads {company} carrying {packs}"


def running_balance(deltas: list[int]) -> list[int]:
    return list(accumulate(deltas))
