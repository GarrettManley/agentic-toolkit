"""Static definition of the tutorial's modules and their skill tags.

Data-driven on purpose: adding a module means adding a row here (and authoring
its files), not wiring anything into the engine. Only modules that have actually
been written are marked ``built=True`` — the rest render as locked/planned, which
is how the dynamic cadence stays decoupled from the scoring code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    """One module's identity, skill tags, and XP weight."""

    id: str
    title: str
    skills: tuple[str, ...]
    base_xp: int
    built: bool


CATALOG: tuple[ModuleSpec, ...] = (
    ModuleSpec("00", "Setup", ("tooling",), 100, built=True),
    ModuleSpec(
        "01",
        "Data model",
        ("data-model", "equality", "hashing", "truthiness", "mutable-defaults"),
        100,
        built=True,
    ),
    ModuleSpec(
        "02",
        "Data structures",
        ("comprehensions", "collections", "unpacking"),
        100,
        built=True,
    ),
    ModuleSpec(
        "02b",
        "Data structures, reforged",
        ("comprehensions", "collections", "unpacking"),
        120,
        built=True,
    ),
    ModuleSpec(
        "03", "Functions", ("closures", "decorators", "functools"), 100, built=False
    ),
    ModuleSpec(
        "04",
        "Iterators & generators",
        ("iterators", "generators", "itertools"),
        100,
        built=False,
    ),
    ModuleSpec(
        "05",
        "Classes Pythonically",
        ("dataclasses", "protocols", "context-managers"),
        100,
        built=False,
    ),
    ModuleSpec(
        "06", "Typing & errors", ("typing", "exceptions", "eafp"), 100, built=False
    ),
    ModuleSpec("07", "Testing & packaging", ("pytest", "packaging"), 100, built=False),
    ModuleSpec("capstone", "Capstone", ("integration",), 300, built=False),
)

_BY_ID: dict[str, ModuleSpec] = {spec.id: spec for spec in CATALOG}


def get(module_id: str) -> ModuleSpec:
    """Return the spec for ``module_id``, or raise ``KeyError`` if unknown."""
    return _BY_ID[module_id]


def built_modules() -> tuple[ModuleSpec, ...]:
    """The modules that have been authored, in catalog order."""
    return tuple(spec for spec in CATALOG if spec.built)
