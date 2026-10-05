"""Rental income tax (extension task A).

Rules from the Income Tax (Amendment) Act 2022, in force from 1 July 2022:

* Individual: 12% of gross annual rent above UGX 2,820,000. Expenses are not
  deductible.
* Company (non-individual): 30% of rent minus expenses. Deductible expenses
  are capped at 50% of gross rent.
"""

from __future__ import annotations

from decimal import Decimal

from uganda_tax.base import Tax, TaxLine, TaxResult, format_rate
from uganda_tax.context import OwnerType, RentalIncome, TaxContext
from uganda_tax.exceptions import NoScheduleForDateError
from uganda_tax.money import Money
from uganda_tax.rates import (
    RENTAL_COMPANY_EXPENSE_CAP,
    RENTAL_COMPANY_RATE,
    RENTAL_INDIVIDUAL_RATE,
    RENTAL_INDIVIDUAL_THRESHOLD,
    RENTAL_PERIOD,
)
from uganda_tax.schedules import EffectivePeriod


class RentalIncomeTax(Tax):
    """Annual rental income tax for individuals and companies."""

    name = "Rental income tax"

    def __init__(
        self,
        period: EffectivePeriod = RENTAL_PERIOD,
        individual_rate: Decimal = RENTAL_INDIVIDUAL_RATE,
        individual_threshold: Money = RENTAL_INDIVIDUAL_THRESHOLD,
        company_rate: Decimal = RENTAL_COMPANY_RATE,
        company_expense_cap: Decimal = RENTAL_COMPANY_EXPENSE_CAP,
    ) -> None:
        """Create a rental income tax calculator with the given rules."""
        self.period = period
        self.individual_rate = individual_rate
        self.individual_threshold = individual_threshold
        self.company_rate = company_rate
        self.company_expense_cap = company_expense_cap

    def _individual(self, rental: RentalIncome) -> TaxResult:
        base = (rental.gross_rent - self.individual_threshold).clamp_at_zero()
        line = TaxLine(label=f"{format_rate(self.individual_rate)} of rent above "
                             f"{self.individual_threshold}",
                       base=base, rate=self.individual_rate, amount=base * self.individual_rate)
        notes: tuple[str, ...] = ()
        if rental.expenses > Money.zero():
            notes = ("Expenses are not deductible for an individual.",)
        return TaxResult(tax_name=self.name, taxable_base=base, amount=line.amount,
                         lines=(line,), notes=notes)

    def _company(self, rental: RentalIncome) -> TaxResult:
        cap = rental.gross_rent * self.company_expense_cap
        allowed = rental.expenses if rental.expenses <= cap else cap
        base = rental.gross_rent - allowed
        line = TaxLine(label=f"{format_rate(self.company_rate)} of chargeable rental income",
                       base=base, rate=self.company_rate, amount=base * self.company_rate)
        notes: tuple[str, ...] = ()
        if allowed < rental.expenses:
            notes = (f"Expenses capped at {format_rate(self.company_expense_cap)} of rent: {cap}.",)
        return TaxResult(tax_name=self.name, taxable_base=base, amount=line.amount,
                         lines=(line,), notes=notes)

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate rental income tax for the year.

        Raises:
            MissingContextDataError: If the context has no rental income.
            NoScheduleForDateError: If ``ctx.on_date`` is before the rules started.
        """
        rental = ctx.require_rental()
        if not self.period.contains(ctx.on_date):
            raise NoScheduleForDateError(self.name, ctx.on_date,
                                         f"The rules apply from {self.period}.")
        if rental.owner_type is OwnerType.INDIVIDUAL:
            return self._individual(rental)
        return self._company(rental)
