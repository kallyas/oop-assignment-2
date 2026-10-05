"""Tests of the payroll pipeline, VAT, corporate tax and the extension modules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from uganda_tax import (
    Band,
    BusinessIncome,
    CorporateIncomeTax,
    EffectivePeriod,
    EmploymentIncome,
    InvalidIncomeError,
    Invoice,
    InvoiceDirection,
    LocalServiceTax,
    MissingContextDataError,
    Money,
    NoScheduleForDateError,
    NoWithholdingRuleError,
    OwnerType,
    Payment,
    PaymentCategory,
    Payroll,
    ProgressiveSchedule,
    RentalIncome,
    RentalIncomeTax,
    Residency,
    SupplyType,
    TaxContext,
    TaxError,
    VatTax,
    WithholdingTax,
)

AUGUST = date(2026, 8, 15)     # an LST instalment month
DECEMBER = date(2026, 12, 15)  # not an LST instalment month


def employment_ctx(gross: int, allowances: int = 0, on_date: date = AUGUST) -> TaxContext:
    return TaxContext(on_date=on_date,
                      employment=EmploymentIncome(Money(gross), Money(allowances)))


# Payroll ----------------------------------------------------------------------

def test_payroll_order_and_net_pay() -> None:
    slip = Payroll(lst=LocalServiceTax()).run(employment_ctx(2_000_000, 500_000))
    assert slip.total_gross == Money(2_500_000)
    assert slip.lst_amount == Money(25_000)                # 100,000 a year / 4
    assert slip.paye.taxable_base == Money(2_475_000)      # LST comes off before PAYE
    assert slip.paye.amount == Money(630_750)              # 33,750 + 30% of 1,990,000
    assert slip.nssf_employee.amount == Money(125_000)     # 5% of gross, not of the PAYE base
    assert slip.nssf_employer.amount == Money(250_000)
    assert slip.net_pay == Money(2_500_000 - 25_000 - 630_750 - 125_000)
    assert slip.employer_cost == Money(2_750_000)


def test_lst_is_zero_outside_instalment_months() -> None:
    slip = Payroll(lst=LocalServiceTax()).run(employment_ctx(2_000_000, on_date=DECEMBER))
    assert slip.lst_amount == Money.zero()
    assert slip.paye.taxable_base == Money(2_000_000)


def test_lst_can_be_turned_off_or_configured() -> None:
    assert Payroll().run(employment_ctx(800_000)).lst is None
    monthly = LocalServiceTax(instalment_months=range(1, 13))
    assert monthly.calculate(employment_ctx(800_000)).amount == Money(70_000) / 12


@pytest.mark.parametrize(("income", "annual"), [
    (100_000, 0), (100_001, 5_000), (500_000, 30_000), (600_001, 60_000),
    (1_000_000, 90_000), (1_000_001, 100_000),
])
def test_lst_bands(income: int, annual: int) -> None:
    assert LocalServiceTax().annual_amount(Money(income)) == Money(annual)


def test_negative_income_is_refused() -> None:
    with pytest.raises(InvalidIncomeError):
        EmploymentIncome(Money(-1))


# VAT -------------------------------------------------------------------------

def vat_ctx(*invoices: Invoice) -> TaxContext:
    return TaxContext(on_date=AUGUST, invoices=invoices)


def test_vat_standard_zero_and_exempt() -> None:
    ctx = vat_ctx(
        Invoice("S1", InvoiceDirection.SALE, SupplyType.STANDARD, Money(10_000_000)),
        Invoice("S2", InvoiceDirection.SALE, SupplyType.ZERO_RATED, Money(4_000_000)),
        Invoice("S3", InvoiceDirection.SALE, SupplyType.EXEMPT, Money(2_000_000)),
        Invoice("P1", InvoiceDirection.PURCHASE, SupplyType.STANDARD, Money(5_000_000)),
        Invoice("P2", InvoiceDirection.PURCHASE, SupplyType.EXEMPT, Money(1_000_000)),
    )
    vat = VatTax()
    assert vat.output_vat(ctx) == Money(1_800_000)
    assert vat.input_vat(ctx) == Money(900_000)
    result = vat.calculate(ctx)
    assert result.amount == Money(900_000)
    assert result.taxable_base == Money(14_000_000)   # exempt sales are not taxable supplies
    assert sum((line.amount for line in result.lines), Money.zero()) == result.amount


def test_vat_credit_when_input_is_larger() -> None:
    ctx = vat_ctx(
        Invoice("S1", InvoiceDirection.SALE, SupplyType.ZERO_RATED, Money(8_000_000)),
        Invoice("P1", InvoiceDirection.PURCHASE, SupplyType.STANDARD, Money(3_000_000)),
    )
    result = VatTax().calculate(ctx)
    assert result.amount == Money(-540_000)
    assert "credit" in result.notes[-1]


def test_vat_needs_invoices() -> None:
    with pytest.raises(MissingContextDataError):
        VatTax().calculate(vat_ctx())


# Corporate income tax ----------------------------------------------------------

def test_corporate_tax() -> None:
    ctx = TaxContext(on_date=AUGUST, business=BusinessIncome(Money(900_000_000),
                                                             Money(600_000_000)))
    result = CorporateIncomeTax().calculate(ctx)
    assert result.taxable_base == Money(300_000_000)
    assert result.amount == Money(90_000_000)


def test_corporate_loss_gives_zero_tax_and_a_note() -> None:
    ctx = TaxContext(on_date=AUGUST, business=BusinessIncome(Money(100), Money(250)))
    result = CorporateIncomeTax().calculate(ctx)
    assert result.amount == Money.zero()
    assert "loss of UGX 150" in result.notes[0]


# Extension A: withholding tax and rental income tax -----------------------------

def wht(category: PaymentCategory, amount: int,
        residency: Residency = Residency.RESIDENT, listed: bool = False) -> Money:
    payment = Payment(category, Money(amount), residency, listed_company_dividend=listed)
    return WithholdingTax().calculate(TaxContext(on_date=AUGUST, payment=payment)).amount


def test_withholding_tax_rates_and_threshold() -> None:
    assert wht(PaymentCategory.SUPPLIES, 1_000_000) == Money(0)
    assert wht(PaymentCategory.SUPPLIES, 1_000_001) == Money(60_000)
    assert wht(PaymentCategory.PROFESSIONAL_FEES, 2_000_000) == Money(120_000)
    assert wht(PaymentCategory.PROFESSIONAL_FEES, 2_000_000, Residency.NON_RESIDENT) == Money(300_000)
    assert wht(PaymentCategory.DIVIDENDS, 1_000_000) == Money(150_000)
    assert wht(PaymentCategory.DIVIDENDS, 1_000_000, listed=True) == Money(100_000)
    with pytest.raises(NoWithholdingRuleError):
        wht(PaymentCategory.SUPPLIES, 5_000_000, Residency.NON_RESIDENT)


def rental(owner: OwnerType, rent: int, expenses: int = 0,
           on_date: date = AUGUST) -> Money:
    ctx = TaxContext(on_date=on_date, rental=RentalIncome(owner, Money(rent), Money(expenses)))
    return RentalIncomeTax().calculate(ctx).amount


def test_rental_income_tax() -> None:
    assert rental(OwnerType.INDIVIDUAL, 2_820_000) == Money(0)
    assert rental(OwnerType.INDIVIDUAL, 12_820_000, expenses=5_000_000) == Money(1_200_000)
    assert rental(OwnerType.COMPANY, 10_000_000, expenses=2_000_000) == Money(2_400_000)
    assert rental(OwnerType.COMPANY, 10_000_000, expenses=8_000_000) == Money(1_500_000)
    with pytest.raises(NoScheduleForDateError):
        rental(OwnerType.INDIVIDUAL, 5_000_000, on_date=date(2021, 1, 1))


# Validation of rules -------------------------------------------------------------

def test_bad_schedules_are_refused() -> None:
    with pytest.raises(TaxError):
        Band(Money(0), Money(100), Decimal("1.5"))
    with pytest.raises(TaxError):
        ProgressiveSchedule(name="gap", residency=Residency.RESIDENT,
                            period=EffectivePeriod(date(2026, 7, 1)),
                            bands=(Band(Money(0), Money(100), Decimal(0)),))
    with pytest.raises(TaxError):
        EffectivePeriod(date(2026, 7, 1), date(2026, 6, 1))
