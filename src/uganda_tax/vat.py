"""Value Added Tax (VAT) for one VAT period."""

from __future__ import annotations

from decimal import Decimal

from uganda_tax.base import Tax, TaxLine, TaxResult
from uganda_tax.context import Invoice, InvoiceDirection, SupplyType, TaxContext
from uganda_tax.exceptions import MissingContextDataError, TaxError
from uganda_tax.money import Money
from uganda_tax.rates import VAT_STANDARD_RATE


class VatTax(Tax):
    """Output VAT, input VAT and net VAT payable for a list of invoices.

    * Standard-rated supplies: VAT at the standard rate (18%).
    * Zero-rated supplies: VAT at 0%. The supply is taxable, so input VAT on
      related purchases can still be claimed.
    * Exempt supplies: no VAT is charged, and no input VAT is claimed.

    A negative result is a VAT credit, which can be carried forward or refunded.
    This model does not split input VAT for a business with both taxable
    and exempt sales (partial exemption).
    """

    name = "VAT"

    def __init__(self, standard_rate: Decimal = VAT_STANDARD_RATE) -> None:
        """Create a VAT calculator with the given standard rate."""
        if not Decimal(0) < standard_rate < Decimal(1):
            raise TaxError(f"VAT rate {standard_rate} must be between 0 and 1.")
        self.rates: dict[SupplyType, Decimal] = {
            SupplyType.STANDARD: standard_rate,
            SupplyType.ZERO_RATED: Decimal(0),
            SupplyType.EXEMPT: Decimal(0),
        }

    def vat_on(self, invoice: Invoice) -> Money:
        """Return the VAT on one invoice."""
        return invoice.net_amount * self.rates[invoice.supply_type]

    def _total(self, invoices: tuple[Invoice, ...], direction: InvoiceDirection) -> Money:
        return sum(
            (self.vat_on(invoice) for invoice in invoices if invoice.direction is direction),
            Money.zero(),
        )

    def output_vat(self, ctx: TaxContext) -> Money:
        """Return the VAT charged on sales."""
        return self._total(ctx.invoices, InvoiceDirection.SALE)

    def input_vat(self, ctx: TaxContext) -> Money:
        """Return the VAT paid on purchases that can be claimed."""
        return self._total(ctx.invoices, InvoiceDirection.PURCHASE)

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Return net VAT payable (output VAT minus input VAT).

        Raises:
            MissingContextDataError: If the context has no invoices.
        """
        if not ctx.invoices:
            raise MissingContextDataError("VAT needs at least one invoice in the context.")
        lines: list[TaxLine] = []
        for invoice in ctx.invoices:
            vat = self.vat_on(invoice)
            sign = 1 if invoice.direction is InvoiceDirection.SALE else -1
            label = f"{invoice.number}: {invoice.direction.value}, {invoice.supply_type.value}"
            lines.append(TaxLine(label=label, base=invoice.net_amount,
                                 rate=self.rates[invoice.supply_type], amount=vat * sign))
        output_vat, input_vat = self.output_vat(ctx), self.input_vat(ctx)
        net = output_vat - input_vat
        taxable_sales = sum(
            (i.net_amount for i in ctx.invoices
             if i.direction is InvoiceDirection.SALE and i.supply_type is not SupplyType.EXEMPT),
            Money.zero(),
        )
        notes = [f"Output VAT {output_vat}; input VAT {input_vat}."]
        if net.is_negative():
            notes.append(f"VAT credit of {-net} to carry forward or claim as a refund.")
        return TaxResult(tax_name=self.name, taxable_base=taxable_sales, amount=net,
                         lines=tuple(lines), notes=tuple(notes))
