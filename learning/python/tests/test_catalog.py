import pathlib

import pytest

from sprint import catalog


def test_module_ids_are_unique():
    ids = [spec.id for spec in catalog.CATALOG]
    assert len(ids) == len(set(ids))


def _module_dir(module_id: str) -> pathlib.Path | None:
    """The ``modules/`` directory for ``module_id``, or None if unauthored."""
    root = pathlib.Path(__file__).resolve().parents[1] / "modules"
    matches = sorted(root.glob(f"{module_id}-*")) or sorted(root.glob(module_id))
    return matches[0] if matches else None


def test_built_flag_matches_what_is_actually_on_disk():
    """``built=True`` means real files exist; ``built=False`` means none do.

    Derived from the filesystem rather than a hardcoded id set so authoring a new
    module does not require editing this test.
    """
    for spec in catalog.CATALOG:
        directory = _module_dir(spec.id)
        if spec.built:
            assert directory is not None, (
                f"{spec.id} is built=True but has no directory"
            )
            assert list(directory.glob("test_*.py")), f"{spec.id} has no test file"
            assert list(directory.glob("[ce]*.py")), (
                f"{spec.id} has no exercise/check file"
            )
        else:
            assert directory is None, f"{spec.id} is built=False but {directory} exists"


def test_every_authored_module_has_a_reference_solution():
    solutions = pathlib.Path(__file__).resolve().parents[1] / "solutions"
    for spec in catalog.built_modules():
        directory = _module_dir(spec.id)
        assert directory is not None
        assert (solutions / f"{directory.name}.py").exists(), (
            f"missing solutions/{directory.name}.py"
        )


def test_get_unknown_module_raises_keyerror():
    with pytest.raises(KeyError):
        catalog.get("does-not-exist")


def test_capstone_is_worth_more():
    assert catalog.get("capstone").base_xp == 300
