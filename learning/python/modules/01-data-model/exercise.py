from __future__ import annotations

class Money:
    """An immutable amount in integer minor units (cents) plus a currency."""

    def __init__(self, cents: int, currency: str = "USD") -> None:
        self.cents = cents
        self.currency = currency

    def __repr__(self) -> str:
        return f"Money(cents={self.cents}, currency={self.currency!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.cents == other.cents and self.currency == other.currency
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash((self.currency, self.cents))

    def __bool__(self) -> bool:
        return self.cents != 0


def running_total(amount: Money, ledger: list[Money] | None = None) -> list[Money]:
    if ledger is None:
        ledger = []
    ledger.append(amount)
    return ledger
