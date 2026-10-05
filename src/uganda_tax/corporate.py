"""Corporate income tax."""

from __future__ import annotations

from decimal import Decimal

from uganda_tax.base import Tax, TaxLine, TaxResult, format_rate
from uganda_tax.context import TaxContext
from uganda_tax.exceptions import TaxError
from uganda_tax.rates import CORPORATE_TAX_RATE


class CorporateIncomeTax(Tax):
    """Corporate income tax: ``rate * (revenue - allowable deductions)``.

    If the deductions are more than the revenue, the result is a tax loss.
    The tax is then 0, and a note gives the loss to carry forward.
    """

    name = "Corporate income tax"

    def __init__(self, rate: Decimal = CORPORATE_TAX_RATE) -> None:
        """Create a calculator with the given rate (default 30%)."""
        if not Decimal(0) <= rate <= Decimal(1):
            raise TaxError(f"Corporate tax rate {rate} must be between 0 and 1.")
        self.rate = rate

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate corporate income tax.

        Raises:
            MissingContextDataError: If the context has no business income.
        """
        business = ctx.require_business()
        result = business.revenue - business.allowable_deductions
        chargeable = result.clamp_at_zero()
        line = TaxLine(label=f"{format_rate(self.rate)} of chargeable income", base=chargeable,
                       rate=self.rate, amount=chargeable * self.rate)
        notes: tuple[str, ...] = ()
        if result.is_negative():
            notes = (f"Tax loss of {-result} to carry forward.",)
        return TaxResult(tax_name=self.name, taxable_base=chargeable, amount=line.amount,
                         lines=(line,), notes=notes)
