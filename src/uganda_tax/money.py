"""The ``Money`` value object for amounts in Uganda shillings (UGX).

Rounding rules
--------------
* All amounts are stored as ``decimal.Decimal``. The engine never uses ``float``.
* UGX has no minor unit in use, so every amount is rounded to a whole shilling.
* Rounding mode is ``ROUND_HALF_UP`` (0.5 goes up, -0.5 goes down to -1).
* Rounding happens when a ``Money`` object is created. So the result of each
  multiplication or division is rounded at once, and a sum of ``Money``
  values is always exact.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import total_ordering
from typing import Final, Union

from uganda_tax.exceptions import InvalidAmountError

#: Input types that ``Money`` accepts. ``float`` is not accepted on purpose.
AmountLike = Union[Decimal, int, str]
#: Types that a ``Money`` value can be multiplied or divided by.
Factor = Union[Decimal, int]

CURRENCY: Final = "UGX"
QUANTUM: Final = Decimal("1")
ROUNDING: Final = ROUND_HALF_UP


def to_decimal(value: AmountLike) -> Decimal:
    """Convert ``value`` to a finite ``Decimal``.

    Args:
        value: A ``Decimal``, ``int`` or numeric string.

    Returns:
        The value as a ``Decimal``.

    Raises:
        InvalidAmountError: If the value is a ``float`` or ``bool``, is not
            numeric, or is not finite.
    """
    if isinstance(value, (float, bool)) or not isinstance(value, (Decimal, int, str)):
        raise InvalidAmountError(
            f"Use Decimal, int or str for amounts, not {type(value).__name__}."
        )
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise InvalidAmountError(f"{value!r} is not a valid number.") from error
    if not result.is_finite():
        raise InvalidAmountError(f"{value!r} is not a finite number.")
    return result


@total_ordering
class Money:
    """An immutable amount in UGX, rounded to a whole shilling.

    Examples:
        >>> Money(1500) + Money("250.5")
        Money('1751')
        >>> Money(335_000) * Decimal("0.2")
        Money('67000')
        >>> str(Money(1234567))
        'UGX 1,234,567'
    """

    __slots__ = ("_amount",)

    def __init__(self, amount: AmountLike = 0) -> None:
        """Create a ``Money`` value and round it to a whole shilling.

        Raises:
            InvalidAmountError: If ``amount`` is a ``float`` or is not a finite number.
        """
        rounded = to_decimal(amount).quantize(QUANTUM, rounding=ROUNDING)
        # Adding Decimal 0 changes "-0" into "0", so UGX -0 is never shown.
        self._amount: Decimal = rounded + 0

    @classmethod
    def zero(cls) -> Money:
        """Return UGX 0."""
        return cls(0)

    @property
    def amount(self) -> Decimal:
        """The rounded amount as a ``Decimal``."""
        return self._amount

    @property
    def currency(self) -> str:
        """The ISO 4217 currency code (always ``"UGX"``)."""
        return CURRENCY

    def is_negative(self) -> bool:
        """Return ``True`` if the amount is less than zero."""
        return self._amount < 0

    def clamp_at_zero(self) -> Money:
        """Return this amount, or UGX 0 if this amount is negative."""
        return self if self._amount >= 0 else Money.zero()

    # Arithmetic ---------------------------------------------------------

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._amount + other._amount)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._amount - other._amount)

    def __mul__(self, factor: Factor) -> Money:
        # Money * Money has no meaning, and float is not safe, so both are refused.
        if isinstance(factor, (float, bool)) or not isinstance(factor, (Decimal, int)):
            return NotImplemented
        return Money(self._amount * factor)

    def __rmul__(self, factor: Factor) -> Money:
        return self.__mul__(factor)

    def __truediv__(self, divisor: Factor) -> Money:
        if isinstance(divisor, (float, bool)) or not isinstance(divisor, (Decimal, int)):
            return NotImplemented
        if divisor == 0:
            raise InvalidAmountError("Cannot divide money by zero.")
        return Money(self._amount / Decimal(divisor))

    def __neg__(self) -> Money:
        return Money(-self._amount)

    # Comparison ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount == other._amount

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount < other._amount

    def __hash__(self) -> int:
        return hash((CURRENCY, self._amount))

    # Display ------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Money('{self._amount}')"

    def __str__(self) -> str:
        return f"{CURRENCY} {self._amount:,}"
