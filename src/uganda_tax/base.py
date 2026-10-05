"""The abstract ``Tax`` base class and the ``TaxResult`` value object."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from uganda_tax.context import TaxContext
from uganda_tax.money import Money


def format_rate(rate: Decimal) -> str:
    """Return a rate as a percentage without extra zeros, for example ``"10%"`` or ``"0.5%"``."""
    return f"{(rate * 100).normalize():f}%"


@dataclass(frozen=True)
class TaxLine:
    """One line of a tax calculation, for example one PAYE band.

    Attributes:
        label: A short description of the line.
        base: The amount that the rate applies to.
        rate: The rate as a fraction (``Decimal("0.2")`` is 20%).
        amount: ``base * rate``, rounded to a whole shilling.
    """

    label: str
    base: Money
    rate: Decimal
    amount: Money


@dataclass(frozen=True)
class TaxResult:
    """The result of one tax calculation.

    Attributes:
        tax_name: The name of the tax.
        taxable_base: The amount that the tax was charged on.
        amount: The tax due. For VAT, a negative amount is a credit.
        lines: The steps of the calculation. Their amounts add up to ``amount``.
        notes: Readable remarks, for example the schedule that was used.
    """

    tax_name: str
    taxable_base: Money
    amount: Money
    lines: tuple[TaxLine, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def effective_rate(self) -> Decimal:
        """Tax as a fraction of the taxable base (0 if the base is 0)."""
        if self.taxable_base.amount == 0:
            return Decimal(0)
        return self.amount.amount / self.taxable_base.amount

    def __str__(self) -> str:
        return f"{self.tax_name}: {self.amount} on {self.taxable_base}"


class Tax(ABC):
    """Abstract base class for every tax in the engine.

    A subclass gives a ``name`` and implements ``calculate``. The rates are
    passed to the constructor, so a test or a new Finance Act can supply
    different rates without changes to the class.
    """

    name: str = "Tax"

    @abstractmethod
    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate this tax for the given context.

        Args:
            ctx: The input data.

        Returns:
            A ``TaxResult`` with the amount due and the calculation lines.

        Raises:
            TaxError: If the input is not valid or no rule applies.
        """

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r})"
