from exercise import (
    assign_mounts,
    by_rarity,
    flatten_hauls,
    label_hauls,
    party_sheet,
    running_balance,
    top_items,
)

HAULS = {
    "Vex": ["rusty dagger", "moonstone"],
    "Mira": ["silver chalice"],
    "Doran": ["dragon scale", "rope", "torch"],
}

CATALOGUE = {
    "moonstone": "rare",
    "rope": "common",
    "torch": "common",
    "dragon scale": "legendary",
}


def test_flatten_hauls_preserves_owner_then_item_order():
    assert flatten_hauls(HAULS) == [
        "rusty dagger",
        "moonstone",
        "silver chalice",
        "dragon scale",
        "rope",
        "torch",
    ]


def test_flatten_hauls_handles_empty_and_empty_packs():
    assert flatten_hauls({}) == []
    assert flatten_hauls({"Vex": [], "Mira": []}) == []


def test_label_hauls_labels_every_entry():
    assert label_hauls([5, 120, 90, 300], 100) == ["meager", "rich", "meager", "rich"]


def test_label_hauls_never_drops_entries():
    golds = [1, 2, 3, 4, 5]
    assert len(label_hauls(golds, 100)) == len(golds)
    assert label_hauls([], 100) == []


def test_label_hauls_threshold_is_inclusive():
    assert label_hauls([100], 100) == ["rich"]


def test_assign_mounts_pairs_in_order():
    assert assign_mounts(["Vex", "Mira"], ["griffon", "mule"]) == {
        "Vex": "griffon",
        "Mira": "mule",
    }


def test_assign_mounts_drops_the_unmatched_tail():
    assert assign_mounts(["Vex", "Mira", "Doran"], ["griffon", "mule"]) == {
        "Vex": "griffon",
        "Mira": "mule",
    }
    assert assign_mounts(["Vex"], ["griffon", "mule"]) == {"Vex": "griffon"}
    assert assign_mounts([], ["griffon"]) == {}


def test_top_items_ranks_by_count():
    items = ["rope", "rope", "torch", "rope", "torch", "dagger"]
    assert top_items(items, 2) == [("rope", 3), ("torch", 2)]


def test_top_items_returns_everything_when_n_is_large():
    assert top_items(["rope", "rope", "torch"], 99) == [("rope", 2), ("torch", 1)]
    assert top_items([], 3) == []


def test_by_rarity_groups_items_under_their_rarity():
    assert by_rarity(CATALOGUE) == {
        "rare": ["moonstone"],
        "common": ["rope", "torch"],
        "legendary": ["dragon scale"],
    }


def test_by_rarity_returns_a_plain_dict_that_invents_nothing():
    result = by_rarity(CATALOGUE)
    assert by_rarity({}) == {}
    assert "mythic" not in result
    result["rare"]  # touching a real key must not change the mapping
    assert set(result) == {"rare", "common", "legendary"}


def test_party_sheet_renders_members_and_gear():
    assert (
        party_sheet("Vex", "Mira", "Doran", rope=2, torch=1)
        == "Vex leads Mira, Doran carrying rope x2, torch x1"
    )


def test_party_sheet_with_no_members():
    assert party_sheet("Vex", rope=1) == "Vex leads nobody carrying rope x1"


def test_party_sheet_with_no_gear():
    assert party_sheet("Vex", "Mira") == "Vex leads Mira carrying nothing"


def test_party_sheet_alone_and_empty_handed():
    assert party_sheet("Vex") == "Vex leads nobody carrying nothing"


def test_running_balance_is_cumulative():
    assert running_balance([10, -3, 5]) == [10, 7, 12]


def test_running_balance_edges():
    assert running_balance([]) == []
    assert running_balance([7]) == [7]
    assert running_balance([0, 0, 0]) == [0, 0, 0]
