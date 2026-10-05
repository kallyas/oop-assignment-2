"""Input records and the ``TaxContext`` that every tax reads from.

``TaxContext`` uses composition: it holds one optional record for each kind of
income or transaction. Each tax reads only the record that it needs. If that
record is missing, the tax raises ``MissingContextDataError`` and does not
guess a value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from uganda_tax.exceptions import InvalidIncomeError, MissingContextDataError
from uganda_tax.money import Money


class Residency(str, Enum):
    """Tax residency of a person or company."""

    RESIDENT = "resident"
    NON_RESIDENT = "non_resident"


class SupplyType(str, Enum):
    """VAT treatment of a supply."""

    STANDARD = "standard"
    ZERO_RATED = "zero_rated"
    EXEMPT = "exempt"


class InvoiceDirection(str, Enum):
    """Whether an invoice is a sale (output VAT) or a purchase (input VAT)."""

    SALE = "sale"
    PURCHASE = "purchase"


class OwnerType(str, Enum):
    """Type of owner for rental income tax."""

    INDIVIDUAL = "individual"
    COMPANY = "company"


class PaymentCategory(str, Enum):
    """Payment categories for withholding tax."""

    SUPPLIES = "supplies of goods or services"
    PROFESSIONAL_FEES = "management or professional fees"
    DIVIDENDS = "dividends"
    INTEREST = "interest"


def require_non_negative(value: Money, label: str) -> None:
    """Raise ``InvalidIncomeError`` if ``value`` is negative.

    Args:
        value: The amount to check.
        label: A readable name for the amount, used in the error message.
    """
    if value.is_negative():
        raise InvalidIncomeError(f"{label} must not be negative, but it is {value}.")


@dataclass(frozen=True)
class EmploymentIncome:
    """One month of employment income for one employee.

    Attributes:
        gross_pay: Monthly gross salary before any deduction.
        allowances: Monthly cash allowances. They are taxable and are part of gross income.
        deductions_before_paye: Amounts that reduce the PAYE base, for example
            Local Service Tax paid in the month. The payroll pipeline sets this value.
    """

    gross_pay: Money
    allowances: Money = field(default_factory=Money.zero)
    deductions_before_paye: Money = field(default_factory=Money.zero)

    def __post_init__(self) -> None:
        require_non_negative(self.gross_pay, "Gross pay")
        require_non_negative(self.allowances, "Allowances")
        require_non_negative(self.deductions_before_paye, "Deductions before PAYE")

    @property
    def total_gross(self) -> Money:
        """Gross pay plus allowances."""
        return self.gross_pay + self.allowances


@dataclass(frozen=True)
class Invoice:
    """A VAT invoice. ``net_amount`` excludes VAT."""

    number: str
    direction: InvoiceDirection
    supply_type: SupplyType
    net_amount: Money

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise InvalidIncomeError("An invoice must have a number.")
        require_non_negative(self.net_amount, f"Net amount of invoice {self.number}")


@dataclass(frozen=True)
class BusinessIncome:
    """Annual business figures of a company for corporate income tax."""

    revenue: Money
    allowable_deductions: Money

    def __post_init__(self) -> None:
        require_non_negative(self.revenue, "Revenue")
        require_non_negative(self.allowable_deductions, "Allowable deductions")


@dataclass(frozen=True)
class RentalIncome:
    """Annual rental income of one owner."""

    owner_type: OwnerType
    gross_rent: Money
    expenses: Money = field(default_factory=Money.zero)

    def __post_init__(self) -> None:
        require_non_negative(self.gross_rent, "Gross rent")
        require_non_negative(self.expenses, "Rental expenses")


@dataclass(frozen=True)
class Payment:
    """A payment on which the payer may have to withhold tax."""

    category: PaymentCategory
    gross_amount: Money
    payee_residency: Residency = Residency.RESIDENT
    listed_company_dividend: bool = False

    def __post_init__(self) -> None:
        require_non_negative(self.gross_amount, "Payment amount")


@dataclass(frozen=True)
class TaxContext:
    """All the input data for one tax calculation.

    Attributes:
        on_date: The date that selects the rate schedule.
        residency: Tax residency of the taxpayer.
        employment: Monthly employment income (PAYE, NSSF, LST).
        invoices: VAT invoices for one VAT period.
        business: Annual business figures (corporate income tax).
        rental: Annual rental income (rental income tax).
        payment: One payment (withholding tax).
    """

    on_date: date
    residency: Residency = Residency.RESIDENT
    employment: EmploymentIncome | None = None
    invoices: tuple[Invoice, ...] = ()
    business: BusinessIncome | None = None
    rental: RentalIncome | None = None
    payment: Payment | None = None

    def require_employment(self) -> EmploymentIncome:
        """Return the employment record, or raise ``MissingContextDataError``."""
        if self.employment is None:
            raise MissingContextDataError("This tax needs employment income in the context.")
        return self.employment

    def require_business(self) -> BusinessIncome:
        """Return the business record, or raise ``MissingContextDataError``."""
        if self.business is None:
            raise MissingContextDataError("This tax needs business income in the context.")
        return self.business

    def require_rental(self) -> RentalIncome:
        """Return the rental record, or raise ``MissingContextDataError``."""
        if self.rental is None:
            raise MissingContextDataError("This tax needs rental income in the context.")
        return self.rental

    def require_payment(self) -> Payment:
        """Return the payment record, or raise ``MissingContextDataError``."""
        if self.payment is None:
            raise MissingContextDataError("This tax needs a payment in the context.")
        return self.payment
