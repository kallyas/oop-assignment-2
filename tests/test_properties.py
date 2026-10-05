"""Property-based tests with Hypothesis.

For any income, tax must be non-negative, must not go down when income goes
up (monotonic), and must never be more than the income.
"""

from __future__ import annotations

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from uganda_tax import (
    BusinessIncome,
    CorporateIncomeTax,
    EmploymentIncome,
    LocalServiceTax,
    Money,
    OwnerType,
    PayeTax,
    Payroll,
    RentalIncome,
    RentalIncomeTax,
    Residency,
    TaxContext,
)

incomes = st.integers(min_value=0, max_value=10**11)
residencies = st.sampled_from(list(Residency))
dates = st.dates(min_value=date(2012, 7, 1), max_value=date(2030, 12, 31))


def paye(income: int, residency: Residency, on_date: date) -> Money:
    ctx = TaxContext(on_date=on_date, residency=residency,
                     employment=EmploymentIncome(Money(income)))
    return PayeTax().calculate(ctx).amount


@given(incomes, residencies, dates)
def test_paye_is_non_negative_and_not_more_than_income(
        income: int, residency: Residency, on_date: date) -> None:
    tax = paye(income, residency, on_date)
    assert Money.zero() <= tax <= Money(income)


@given(incomes, incomes, residencies, dates)
def test_paye_is_monotonic_in_income(
        first: int, second: int, residency: Residency, on_date: date) -> None:
    low, high = sorted((first, second))
    assert paye(low, residency, on_date) <= paye(high, residency, on_date)


@given(incomes, incomes, dates)
def test_net_pay_is_between_zero_and_gross(gross: int, allowances: int, on_date: date) -> None:
    ctx = TaxContext(on_date=on_date,
                     employment=EmploymentIncome(Money(gross), Money(allowances)))
    slip = Payroll(lst=LocalServiceTax()).run(ctx)
    assert Money.zero() <= slip.net_pay <= slip.total_gross


@given(incomes, incomes)
def test_corporate_tax_properties(revenue: int, deductions: int) -> None:
    def tax(rev: int) -> Money:
        ctx = TaxContext(on_date=date(2026, 7, 1),
                         business=BusinessIncome(Money(rev), Money(deductions)))
        return CorporateIncomeTax().calculate(ctx).amount

    assert Money.zero() <= tax(revenue) <= Money(revenue)
    assert tax(revenue) <= tax(revenue + 1_000)


@given(st.sampled_from(list(OwnerType)), incomes, incomes)
def test_rental_tax_properties(owner: OwnerType, rent: int, expenses: int) -> None:
    def tax(gross_rent: int) -> Money:
        ctx = TaxContext(on_date=date(2026, 7, 1),
                         rental=RentalIncome(owner, Money(gross_rent), Money(expenses)))
        return RentalIncomeTax().calculate(ctx).amount

    assert Money.zero() <= tax(rent) <= Money(rent)
    assert tax(rent) <= tax(rent + 1_000)
