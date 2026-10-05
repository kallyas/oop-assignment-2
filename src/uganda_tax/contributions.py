"""Payroll charges other than PAYE: NSSF contributions and Local Service Tax."""

from __future__ import annotations

from collections.abc import Collection
from decimal import Decimal

from uganda_tax.base import Tax, TaxLine, TaxResult, format_rate
from uganda_tax.context import TaxContext
from uganda_tax.exceptions import TaxError
from uganda_tax.money import Money
from uganda_tax.rates import (
    LST_ANNUAL_BANDS,
    LST_INSTALMENT_MONTHS,
    NSSF_EMPLOYEE_RATE,
    NSSF_EMPLOYER_RATE,
)


class NssfContribution(Tax):
    """An NSSF contribution at a flat rate of total gross pay.

    The employee share and the employer share are two instances of this one
    class with different rates. They do not need two subclasses.
    """

    def __init__(self, rate: Decimal, party: str) -> None:
        """Create an NSSF contribution.

        Args:
            rate: The contribution rate, for example ``Decimal("0.05")``.
            party: ``"employee"`` or ``"employer"``.
        """
        if not Decimal(0) <= rate <= Decimal(1):
            raise TaxError(f"NSSF rate {rate} must be between 0 and 1.")
        self.rate = rate
        self.party = party
        self.name = f"NSSF ({party})"

    @classmethod
    def employee(cls) -> NssfContribution:
        """The 5% employee contribution."""
        return cls(NSSF_EMPLOYEE_RATE, "employee")

    @classmethod
    def employer(cls) -> NssfContribution:
        """The 10% employer contribution."""
        return cls(NSSF_EMPLOYER_RATE, "employer")

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate the contribution on gross pay plus allowances."""
        base = ctx.require_employment().total_gross
        line = TaxLine(label=f"{format_rate(self.rate)} of gross", base=base, rate=self.rate,
                       amount=base * self.rate)
        return TaxResult(tax_name=self.name, taxable_base=base, amount=line.amount, lines=(line,))


class LocalServiceTax(Tax):
    """Local Service Tax (LST), paid to the local government.

    The annual amount depends on the monthly gross income band. The employer
    deducts it in equal instalments in the instalment months (July to
    October by default). In other months the deduction is 0.
    """

    name = "Local Service Tax"

    def __init__(
        self,
        annual_bands: tuple[tuple[Money | None, Money], ...] = LST_ANNUAL_BANDS,
        instalment_months: Collection[int] = LST_INSTALMENT_MONTHS,
    ) -> None:
        """Create an LST calculator.

        Args:
            annual_bands: ``(upper monthly income, annual LST)`` pairs in
                increasing order. The last upper limit must be ``None``.
            instalment_months: Calendar months (1-12) in which LST is deducted.
        """
        if not annual_bands or annual_bands[-1][0] is not None:
            raise TaxError("The last LST band must have no upper limit.")
        if not instalment_months or not set(instalment_months) <= set(range(1, 13)):
            raise TaxError("LST instalment months must be calendar months from 1 to 12.")
        self.annual_bands = annual_bands
        self.instalment_months = frozenset(instalment_months)

    def annual_amount(self, monthly_income: Money) -> Money:
        """Return the annual LST for a monthly gross income."""
        for upper, annual in self.annual_bands:
            if upper is None or monthly_income <= upper:
                return annual
        raise TaxError("No LST band matched.")  # Not reached: the last band has no top.

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Return the LST instalment for the month of ``ctx.on_date``."""
        income = ctx.require_employment().total_gross
        annual = self.annual_amount(income)
        if ctx.on_date.month not in self.instalment_months:
            return TaxResult(
                tax_name=self.name, taxable_base=income, amount=Money.zero(),
                notes=(f"Month {ctx.on_date.month} is not an LST instalment month.",),
            )
        instalment = annual / len(self.instalment_months)
        line = TaxLine(label=f"Annual LST {annual} / {len(self.instalment_months)} instalments",
                       base=annual, rate=Decimal(1) / len(self.instalment_months), amount=instalment)
        return TaxResult(tax_name=self.name, taxable_base=income, amount=instalment, lines=(line,))
