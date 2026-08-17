from exercise import Money, running_total


def test_repr_round_trips_the_fields():
    assert repr(Money(500, "USD")) == "Money(cents=500, currency='USD')"


def test_equality_is_by_value_not_identity():
    a, b = Money(500, "USD"), Money(500, "USD")
    assert a == b
    assert a is not b


def test_different_currency_is_not_equal():
    assert Money(500, "USD") != Money(500, "EUR")


def test_equality_with_non_money_is_false_not_error():
    assert (Money(500, "USD") == "500") is False


def test_hash_matches_equality():
    a, b = Money(500, "USD"), Money(500, "USD")
    assert hash(a) == hash(b)
    assert {a, b} == {a}
    assert {a: "yes"}[b] == "yes"


def test_truthiness_zero_is_falsy():
    assert not Money(0, "USD")
    assert Money(1, "USD")


def test_running_total_does_not_leak_between_calls():
    assert running_total(Money(100)) == [Money(100)]
    assert running_total(Money(200)) == [Money(200)]


def test_running_total_appends_to_supplied_ledger():
    ledger = [Money(100)]
    result = running_total(Money(200), ledger)
    assert result == [Money(100), Money(200)]
    assert result is ledger
