import pytest

from sprint import catalog


def test_module_ids_are_unique():
    ids = [spec.id for spec in catalog.CATALOG]
    assert len(ids) == len(set(ids))


def test_only_authored_modules_are_built():
    assert catalog.get("00").built is True
    assert catalog.get("01").built is True
    assert catalog.get("02").built is False
    assert {spec.id for spec in catalog.built_modules()} == {"00", "01"}


def test_get_unknown_module_raises_keyerror():
    with pytest.raises(KeyError):
        catalog.get("does-not-exist")


def test_capstone_is_worth_more():
    assert catalog.get("capstone").base_xp == 300
