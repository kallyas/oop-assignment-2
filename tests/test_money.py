"""Tests of the ``Money`` value object."""

from __future__ import annotations

from decimal import Decimal

import pytest

from uganda_tax import InvalidAmountError, Money


def test_rounds_half_up_to_whole_shilling() -> None:
    assert Money("0.5").amount == Decimal(1)
    assert Money("1.49").amount == Decimal(1)
    assert Money("2.5").amount == Decimal(3)
    assert Money("-2.5").amount == Decimal(-3)
    assert repr(Money("-0.4")) == "Money('0')"


def test_float_is_refused() -> None:
    with pytest.raises(InvalidAmountError):
        Money(0.1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Money(100) * 0.18  # type: ignore[operator]


def test_invalid_values_are_refused() -> None:
    for bad in ("abc", "NaN", "Infinity"):
        with pytest.raises(InvalidAmountError):
            Money(bad)


def test_operators() -> None:
    assert Money(100) + Money(50) == Money(150)
    assert Money(100) - Money(150) == Money(-50)
    assert Money(1_000) * Decimal("0.18") == Money(180)
    assert Decimal("0.18") * Money(1_000) == Money(180)
    assert Money(100_000) / 4 == Money(25_000)
    assert Money(10) / 3 == Money(3)
    assert -Money(5) == Money(-5)
    assert Money(1) < Money(2) <= Money(2)
    assert max(Money(3), Money(7)) == Money(7)
    with pytest.raises(TypeError):
        Money(1) * Money(2)  # type: ignore[operator]
    with pytest.raises(InvalidAmountError):
        Money(1) / 0


def test_repr_str_and_hash() -> None:
    assert repr(Money(15_000)) == "Money('15000')"
    assert str(Money(1_234_567)) == "UGX 1,234,567"
    assert len({Money(5), Money("5.0"), Money(6)}) == 2
    assert Money(5) != 5
