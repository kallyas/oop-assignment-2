"""Withholding tax (extension task A)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from uganda_tax.base import Tax, TaxLine, TaxResult, format_rate
from uganda_tax.context import Payment, PaymentCategory, Residency, TaxContext
from uganda_tax.exceptions import NoWithholdingRuleError
from uganda_tax.money import Money
from uganda_tax.rates import WHT_LISTED_DIVIDEND_RATE, WHT_RATES, WHT_SUPPLIES_THRESHOLD


class WithholdingTax(Tax):
    """Tax that a payer withholds from a payment and pays to URA.

    Rules used (URA withholding tax page):

    * Supplies of goods or services to a resident: 6%, only when the payment
      is more than UGX 1,000,000.
    * Management or professional fees: 6% (resident), 15% (non-resident).
    * Dividends: 15%, or 10% for a resident shareholder of a listed company.
    * Interest: 15%.
    """

    name = "Withholding tax"

    def __init__(
        self,
        rates: Mapping[tuple[PaymentCategory, Residency], Decimal] = WHT_RATES,
        supplies_threshold: Money = WHT_SUPPLIES_THRESHOLD,
        listed_dividend_rate: Decimal = WHT_LISTED_DIVIDEND_RATE,
    ) -> None:
        """Create a withholding tax calculator with the given rate table."""
        self.rates = dict(rates)
        self.supplies_threshold = supplies_threshold
        self.listed_dividend_rate = listed_dividend_rate

    def rate_for(self, payment: Payment) -> Decimal:
        """Return the rate for a payment.

        Raises:
            NoWithholdingRuleError: If the table has no rule for this payment.
        """
        key = (payment.category, payment.payee_residency)
        if key not in self.rates:
            raise NoWithholdingRuleError(
                f"No withholding rule for {payment.category.value} paid to a "
                f"{payment.payee_residency.value} payee."
            )
        if (payment.category is PaymentCategory.DIVIDENDS and payment.listed_company_dividend
                and payment.payee_residency is Residency.RESIDENT):
            return self.listed_dividend_rate
        return self.rates[key]

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate the tax to withhold from the payment in ``ctx``."""
        payment = ctx.require_payment()
        rate = self.rate_for(payment)
        if (payment.category is PaymentCategory.SUPPLIES
                and payment.gross_amount <= self.supplies_threshold):
            return TaxResult(
                tax_name=self.name, taxable_base=payment.gross_amount, amount=Money.zero(),
                notes=(f"Payment is not more than {self.supplies_threshold}, so no tax is withheld.",),
            )
        line = TaxLine(label=f"{format_rate(rate)} of {payment.category.value}",
                       base=payment.gross_amount, rate=rate, amount=payment.gross_amount * rate)
        return TaxResult(tax_name=self.name, taxable_base=payment.gross_amount,
                         amount=line.amount, lines=(line,),
                         notes=(f"Net amount paid to the payee: {payment.gross_amount - line.amount}.",))
