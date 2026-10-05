"""PAYE tests, with a boundary test at every band edge."""

from __future__ import annotations

from datetime import date

import pytest

from uganda_tax import (
    EmploymentIncome,
    MissingContextDataError,
    Money,
    NoScheduleForDateError,
    PayeTax,
    Residency,
    TaxContext,
)

FY_2026 = date(2026, 10, 1)
FY_2025 = date(2025, 10, 1)


def paye(gross: int, residency: Residency = Residency.RESIDENT, on_date: date = FY_2026,
         allowances: int = 0) -> Money:
    ctx = TaxContext(on_date=on_date, residency=residency,
                     employment=EmploymentIncome(Money(gross), Money(allowances)))
    return PayeTax().calculate(ctx).amount


@pytest.mark.parametrize(("gross", "expected"), [
    (0, 0),
    (335_000, 0),             # top of the nil band
    (335_001, 0),             # 20% of 1 = 0.2, rounds to 0
    (335_005, 1),             # 20% of 5 = 1
    (410_000, 15_000),        # 20% of 75,000
    (410_001, 15_000),        # 15,000 + 25% of 1 = 15,000.25
    (485_000, 33_750),        # 15,000 + 25% of 75,000
    (485_001, 33_750),        # 33,750 + 30% of 1 = 33,750.3
    (10_000_000, 2_888_250),  # 33,750 + 30% of 9,515,000
    (10_000_001, 2_888_250),  # + 30% of 1 + 10% of 1: each line rounds down
    (10_000_010, 2_888_254),  # 30% of 9,515,010 = 2,854,503 and 10% of 10 = 1
    (20_000_000, 6_888_250),  # 33,750 + 30% of 19,515,000 + 10% of 10,000,000
])
def test_resident_2026_band_edges(gross: int, expected: int) -> None:
    assert paye(gross) == Money(expected)


@pytest.mark.parametrize(("gross", "expected"), [
    (0, 0),
    (335_000, 33_500),        # 10% of 335,000
    (335_001, 33_500),
    (410_000, 48_500),        # 33,500 + 20% of 75,000
    (485_000, 71_000),        # 48,500 + 30% of 75,000
    (10_000_000, 2_925_500),  # 48,500 + 30% of 9,590,000
    (10_000_001, 2_925_500),
    (10_000_010, 2_925_504),
])
def test_non_resident_band_edges(gross: int, expected: int) -> None:
    assert paye(gross, Residency.NON_RESIDENT) == Money(expected)


@pytest.mark.parametrize(("gross", "expected"), [
    (235_000, 0),
    (335_000, 10_000),
    (410_000, 25_000),
    (10_000_000, 2_902_000),
])
def test_resident_scale_before_july_2026(gross: int, expected: int) -> None:
    assert paye(gross, on_date=FY_2025) == Money(expected)


def test_schedule_changes_on_1_july_2026() -> None:
    assert paye(400_000, on_date=date(2026, 6, 30)) == Money(23_000)
    assert paye(400_000, on_date=date(2026, 7, 1)) == Money(13_000)


def test_allowances_are_taxable() -> None:
    assert paye(400_000, allowances=85_000) == paye(485_000)


def test_lines_add_up_and_name_the_schedule() -> None:
    ctx = TaxContext(on_date=FY_2026, employment=EmploymentIncome(Money(12_000_000)))
    result = PayeTax().calculate(ctx)
    assert sum((line.amount for line in result.lines), Money.zero()) == result.amount
    assert any("10% over 10,000,000" in line.label for line in result.lines)
    assert "FY 2026/27" in result.notes[0]


def test_date_before_any_schedule_raises() -> None:
    with pytest.raises(NoScheduleForDateError, match="2010-01-31"):
        paye(500_000, on_date=date(2010, 1, 31))


def test_missing_employment_raises() -> None:
    with pytest.raises(MissingContextDataError):
        PayeTax().calculate(TaxContext(on_date=FY_2026))
