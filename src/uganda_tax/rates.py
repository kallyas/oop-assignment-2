"""Official rates used by the engine, with their sources.

All rates were checked on 5 October 2026 against these sources:

* [ura.go] URA, "PAYE rates", https://ura.go.ug/en/domestic-taxes/paye-rates/
  (resident scale in force from 1 July 2026, Income Tax (Amendment) Act 2026).
* [pulse] https://www.pulse.ug/story/uganda-new-paye-rates-2026-guide-2026091410372290209
  (2026 bands, in force from 1 July 2026).
* [calculator.sunpro] https://calculator.sunpro.africa/uganda-income-taxation
  (NSSF 5% / 10% of gross; LST in four instalments, July to October; the 2012 scale).
* [leadafrik] https://leadafrik.com/tax-rates-uganda (VAT 18%, corporate tax 30%).
* [taxatlas] https://taxatlas.io/country/uganda (corporate tax 30%, VAT 18%).
* [afrotools] https://afrotools.com/uganda/ug-paye (LST deducted before PAYE;
  employee NSSF does not reduce the PAYE base).
* URA, "Withholding Tax", https://ura.go.ug/en/witholding-tax/ (extension A).
* Income Tax (Amendment) Act 2022 for the rental income tax rules (extension A).
* Local Governments (Amendment) Act 2008 for the LST bands.

Check these values again before you use the engine for a real tax return.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Final

from uganda_tax.context import PaymentCategory, Residency
from uganda_tax.money import Money
from uganda_tax.schedules import Band, EffectivePeriod, ProgressiveSchedule, make_bands

URA_PAYE_SOURCE: Final = (
    "URA PAYE rates page (https://ura.go.ug/en/domestic-taxes/paye-rates/), checked 2026-10-05"
)

#: The additional 10% on monthly income above UGX 10,000,000 (all PAYE scales).
PAYE_SURCHARGE: Final = (Band(lower=Money(10_000_000), upper=None, rate=Decimal("0.10")),)

#: Resident scale from 1 July 2026 (the baseline in the assignment brief).
RESIDENT_PAYE_2026: Final = ProgressiveSchedule(
    name="Resident monthly PAYE, FY 2026/27 onwards",
    residency=Residency.RESIDENT,
    period=EffectivePeriod(start=date(2026, 7, 1)),
    bands=make_bands([335_000, 410_000, 485_000], ["0", "0.20", "0.25", "0.30"]),
    surcharges=PAYE_SURCHARGE,
    source=URA_PAYE_SOURCE,
)

#: Earlier resident scale (Income Tax (Amendment) Act 2012), up to 30 June 2026.
#: It is included to show how the engine selects a schedule by date.
RESIDENT_PAYE_2012: Final = ProgressiveSchedule(
    name="Resident monthly PAYE, FY 2012/13 to FY 2025/26",
    residency=Residency.RESIDENT,
    period=EffectivePeriod(start=date(2012, 7, 1), end=date(2026, 6, 30)),
    bands=make_bands([235_000, 335_000, 410_000], ["0", "0.10", "0.20", "0.30"]),
    surcharges=PAYE_SURCHARGE,
    source="Income Tax (Amendment) Act 2012",
)

#: Non-resident scale. The 2026 amendment did not change it.
NON_RESIDENT_PAYE: Final = ProgressiveSchedule(
    name="Non-resident monthly PAYE",
    residency=Residency.NON_RESIDENT,
    period=EffectivePeriod(start=date(2012, 7, 1)),
    bands=make_bands([335_000, 410_000], ["0.10", "0.20", "0.30"]),
    surcharges=PAYE_SURCHARGE,
    source=URA_PAYE_SOURCE,
)

DEFAULT_PAYE_SCHEDULES: Final = (RESIDENT_PAYE_2026, RESIDENT_PAYE_2012, NON_RESIDENT_PAYE)

# NSSF -----------------------------------------------------------------------
NSSF_EMPLOYEE_RATE: Final = Decimal("0.05")
NSSF_EMPLOYER_RATE: Final = Decimal("0.10")

# VAT and corporate income tax --------------------------------------------------
VAT_STANDARD_RATE: Final = Decimal("0.18")
CORPORATE_TAX_RATE: Final = Decimal("0.30")

# Local Service Tax ------------------------------------------------------------
#: (upper limit of monthly income, annual LST). ``None`` means no upper limit.
LST_ANNUAL_BANDS: Final[tuple[tuple[Money | None, Money], ...]] = (
    (Money(100_000), Money(0)),
    (Money(200_000), Money(5_000)),
    (Money(300_000), Money(10_000)),
    (Money(400_000), Money(20_000)),
    (Money(500_000), Money(30_000)),
    (Money(600_000), Money(40_000)),
    (Money(700_000), Money(60_000)),
    (Money(800_000), Money(70_000)),
    (Money(900_000), Money(80_000)),
    (Money(1_000_000), Money(90_000)),
    (None, Money(100_000)),
)
#: LST is usually paid in four equal instalments, July to October.
LST_INSTALMENT_MONTHS: Final = frozenset({7, 8, 9, 10})

# Withholding tax (extension A) --------------------------------------------------
WHT_SUPPLIES_THRESHOLD: Final = Money(1_000_000)
WHT_LISTED_DIVIDEND_RATE: Final = Decimal("0.10")
WHT_RATES: Final[dict[tuple[PaymentCategory, Residency], Decimal]] = {
    (PaymentCategory.SUPPLIES, Residency.RESIDENT): Decimal("0.06"),
    (PaymentCategory.PROFESSIONAL_FEES, Residency.RESIDENT): Decimal("0.06"),
    (PaymentCategory.PROFESSIONAL_FEES, Residency.NON_RESIDENT): Decimal("0.15"),
    (PaymentCategory.DIVIDENDS, Residency.RESIDENT): Decimal("0.15"),
    (PaymentCategory.DIVIDENDS, Residency.NON_RESIDENT): Decimal("0.15"),
    (PaymentCategory.INTEREST, Residency.RESIDENT): Decimal("0.15"),
    (PaymentCategory.INTEREST, Residency.NON_RESIDENT): Decimal("0.15"),
}

# Rental income tax (extension A) ------------------------------------------------
RENTAL_PERIOD: Final = EffectivePeriod(start=date(2022, 7, 1))
RENTAL_INDIVIDUAL_RATE: Final = Decimal("0.12")
RENTAL_INDIVIDUAL_THRESHOLD: Final = Money(2_820_000)
RENTAL_COMPANY_RATE: Final = Decimal("0.30")
RENTAL_COMPANY_EXPENSE_CAP: Final = Decimal("0.50")
