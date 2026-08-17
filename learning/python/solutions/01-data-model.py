"""Reference answer for Module 01. Attempt the exercise first."""

from __future__ import annotations


class Money:
    def __init__(self, cents: int, currency: str = "USD") -> None:
        self.cents = cents
        self.currency = currency

    def __repr__(self) -> str:
        return f"Money(cents={self.cents}, currency={self.currency!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return (self.cents, self.currency) == (other.cents, other.currency)

    def __hash__(self) -> int:
        return hash((self.cents, self.currency))

    def __bool__(self) -> bool:
        return self.cents != 0


def running_total(amount: Money, ledger: list[Money] | None = None) -> list[Money]:
    if ledger is None:
        ledger = []
    ledger.append(amount)
    return ledger
