"""Module 01 -- Python's data model.

Implement each ``TODO``, then run:  uv run pytest modules/01-data-model -v
"""

from __future__ import annotations


class Money:
    """An immutable amount in integer minor units (cents) plus a currency."""

    def __init__(self, cents: int, currency: str = "USD") -> None:
        self.cents = cents
        self.currency = currency

    def __repr__(self) -> str:
        """TODO: return a string like  Money(cents=500, currency='USD').

        Use an f-string. ``{self.currency!r}`` gives you the single quotes for
        free (``!r`` calls ``repr`` on the value).
        """
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        """TODO: two Money are equal iff cents AND currency match.

        If ``other`` is not a Money, return ``NotImplemented`` (not ``False``,
        and do not raise) -- that lets Python try the reflected comparison.
        ``isinstance`` is your friend.
        """
        raise NotImplementedError

    def __hash__(self) -> int:
        """TODO: return a hash consistent with __eq__ (equal objects hash equal).

        The idiomatic move: hash a tuple of the fields you compare in __eq__.
        """
        raise NotImplementedError

    def __bool__(self) -> bool:
        """TODO: a zero-cents Money is falsy; any non-zero amount is truthy."""
        raise NotImplementedError


def running_total(amount: Money, ledger: list[Money] | None = None) -> list[Money]:
    """Append ``amount`` to ``ledger`` and return the ledger.

    TODO: when no ledger is passed, start a fresh one. Do NOT write
    ``ledger: list[Money] = []`` in the signature -- a mutable default is created
    ONCE and shared across every call (the classic trap). Use the None-sentinel
    idiom instead.
    """
    raise NotImplementedError
