from exercise import (
    gold_by_adventurer,
    high_value_items,
    loot_by_adventurer,
    merge_inventories,
    rank_table,
    split_party,
)

# (adventurer, item, gold)
ENTRIES = [
    ("Vex", "rusty dagger", 5),
    ("Mira", "silver chalice", 120),
    ("Vex", "healing potion", 25),
    ("Doran", "dragon scale", 300),
    ("Mira", "rope", 5),
    ("Vex", "moonstone", 90),
]


def test_high_value_items_filters_and_preserves_order():
    assert high_value_items(ENTRIES, 90) == [
        "silver chalice",
        "dragon scale",
        "moonstone",
    ]


def test_high_value_items_threshold_is_inclusive():
    assert "moonstone" in high_value_items(ENTRIES, 90)


def test_high_value_items_can_be_empty():
    assert high_value_items(ENTRIES, 1000) == []


def test_rank_table_is_one_based():
    assert rank_table(["Doran", "Mira", "Vex"]) == {"Doran": 1, "Mira": 2, "Vex": 3}


def test_rank_table_handles_empty():
    assert rank_table([]) == {}


def test_gold_by_adventurer_sums_per_name():
    assert gold_by_adventurer(ENTRIES) == {"Vex": 120, "Mira": 125, "Doran": 300}


def test_gold_by_adventurer_does_not_invent_keys():
    result = gold_by_adventurer(ENTRIES)
    assert "Nobody" not in result
    assert gold_by_adventurer([]) == {}


def test_loot_by_adventurer_groups_in_encounter_order():
    assert loot_by_adventurer(ENTRIES) == {
        "Vex": ["rusty dagger", "healing potion", "moonstone"],
        "Mira": ["silver chalice", "rope"],
        "Doran": ["dragon scale"],
    }


def test_split_party_separates_scout_and_rearguard():
    assert split_party(["Vex", "Mira", "Doran", "Kel"]) == (
        "Vex",
        ["Mira", "Doran"],
        "Kel",
    )


def test_split_party_with_no_middle():
    scout, middle, rear = split_party(["Vex", "Kel"])
    assert (scout, rear) == ("Vex", "Kel")
    assert middle == []
    assert isinstance(middle, list)


def test_merge_inventories_later_wins():
    assert merge_inventories({"rope": 1}, {"torch": 2, "rope": 3}) == {
        "rope": 3,
        "torch": 2,
    }


def test_merge_inventories_accepts_any_number_of_packs():
    assert merge_inventories() == {}
    assert merge_inventories({"rope": 1}) == {"rope": 1}


def test_merge_inventories_does_not_mutate_its_arguments():
    first = {"rope": 1}
    merge_inventories(first, {"rope": 99})
    assert first == {"rope": 1}
