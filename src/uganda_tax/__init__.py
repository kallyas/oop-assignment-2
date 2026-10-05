"""Uganda tax engine: an extensible, testable model of URA tax rules."""

from uganda_tax.base import Tax, TaxLine, TaxResult
from uganda_tax.context import (
    BusinessIncome,
    EmploymentIncome,
    Invoice,
    InvoiceDirection,
    OwnerType,
    Payment,
    PaymentCategory,
    RentalIncome,
    Residency,
    SupplyType,
    TaxContext,
)
from uganda_tax.contributions import LocalServiceTax, NssfContribution
from uganda_tax.corporate import CorporateIncomeTax
from uganda_tax.exceptions import (
    InvalidAmountError,
    InvalidIncomeError,
    MissingContextDataError,
    NoScheduleForDateError,
    NoWithholdingRuleError,
    TaxError,
)
from uganda_tax.money import Money
from uganda_tax.paye import PayeTax
from uganda_tax.payroll import Payroll, Payslip
from uganda_tax.rental import RentalIncomeTax
from uganda_tax.schedules import Band, EffectivePeriod, ProgressiveSchedule
from uganda_tax.vat import VatTax
from uganda_tax.withholding import WithholdingTax

__all__ = [
    "Band",
    "BusinessIncome",
    "CorporateIncomeTax",
    "EffectivePeriod",
    "EmploymentIncome",
    "InvalidAmountError",
    "InvalidIncomeError",
    "Invoice",
    "InvoiceDirection",
    "LocalServiceTax",
    "MissingContextDataError",
    "Money",
    "NoScheduleForDateError",
    "NoWithholdingRuleError",
    "NssfContribution",
    "OwnerType",
    "PayeTax",
    "Payment",
    "PaymentCategory",
    "Payroll",
    "Payslip",
    "ProgressiveSchedule",
    "RentalIncome",
    "RentalIncomeTax",
    "Residency",
    "SupplyType",
    "Tax",
    "TaxContext",
    "TaxError",
    "TaxLine",
    "TaxResult",
    "VatTax",
    "WithholdingTax",
]
