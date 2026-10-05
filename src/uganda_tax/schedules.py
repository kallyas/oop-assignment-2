"""Rate bands, dated progressive schedules, and schedule lookup by date."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, TypeVar

from uganda_tax.base import TaxLine, format_rate
from uganda_tax.context import Residency
from uganda_tax.exceptions import NoScheduleForDateError, TaxError
from uganda_tax.money import Money


@dataclass(frozen=True)
class EffectivePeriod:
    """A date range in which a rule is in force. Both ends are inclusive.

    ``end=None`` means that the rule is still in force.
    """

    start: date
    end: date | None = None

    def __post_init__(self) -> None:
        if self.end is not None and self.end < self.start:
            raise TaxError(f"Period end {self.end} is before period start {self.start}.")

    def contains(self, on_date: date) -> bool:
        """Return ``True`` if ``on_date`` is in this period."""
        return self.start <= on_date and (self.end is None or on_date <= self.end)

    def __str__(self) -> str:
        end = "today" if self.end is None else self.end.isoformat()
        return f"{self.start.isoformat()} to {end}"


@dataclass(frozen=True)
class Band:
    """A slice of income taxed at one marginal rate.

    The band covers income above ``lower`` and up to and including ``upper``.
    ``upper=None`` means that the band has no top.
    """

    lower: Money
    upper: Money | None
    rate: Decimal

    def __post_init__(self) -> None:
        if not Decimal(0) <= self.rate <= Decimal(1):
            raise TaxError(f"Band rate {self.rate} must be between 0 and 1.")
        if self.upper is not None and self.upper <= self.lower:
            raise TaxError(f"Band upper limit {self.upper} must be above {self.lower}.")

    def portion(self, income: Money) -> Money:
        """Return the part of ``income`` that falls in this band."""
        if income <= self.lower:
            return Money.zero()
        top = income if self.upper is None or income < self.upper else self.upper
        return top - self.lower

    @property
    def label(self) -> str:
        """A readable label, for example ``"20% over 335,000 to 410,000"``."""
        rate = format_rate(self.rate)
        if self.upper is None:
            return f"{rate} over {self.lower.amount:,}"
        return f"{rate} over {self.lower.amount:,} to {self.upper.amount:,}"

    def line(self, income: Money) -> TaxLine:
        """Return the calculation line for ``income`` in this band."""
        base = self.portion(income)
        return TaxLine(label=self.label, base=base, rate=self.rate, amount=base * self.rate)


@dataclass(frozen=True)
class ProgressiveSchedule:
    """A dated progressive schedule, such as the monthly PAYE scale.

    Attributes:
        name: A readable name for the schedule.
        residency: The residency that the schedule applies to.
        period: The dates on which the schedule is in force.
        bands: Contiguous bands that start at 0. The last band has no top.
        surcharges: Extra bands that are charged on top of ``bands``
            (for example, the additional 10% above UGX 10,000,000).
        source: The legal or official source of the rates.
    """

    name: str
    residency: Residency
    period: EffectivePeriod
    bands: tuple[Band, ...]
    surcharges: tuple[Band, ...] = ()
    source: str = ""

    def __post_init__(self) -> None:
        if not self.bands:
            raise TaxError(f"Schedule {self.name!r} has no bands.")
        if self.bands[0].lower != Money.zero():
            raise TaxError(f"The first band of {self.name!r} must start at 0.")
        for previous, current in zip(self.bands, self.bands[1:]):
            if previous.upper != current.lower:
                raise TaxError(f"The bands of {self.name!r} must be contiguous.")
        if self.bands[-1].upper is not None:
            raise TaxError(f"The last band of {self.name!r} must have no upper limit.")

    def lines_for(self, income: Money) -> tuple[TaxLine, ...]:
        """Return one calculation line for each band and surcharge that ``income`` reaches."""
        all_bands = self.bands + self.surcharges
        return tuple(band.line(income) for band in all_bands if band.portion(income) > Money.zero())

    def tax_on(self, income: Money) -> Money:
        """Return the total tax on ``income`` (the sum of the rounded lines)."""
        return sum((line.amount for line in self.lines_for(income)), Money.zero())


class Dated(Protocol):
    """Any rule that has an ``EffectivePeriod``."""

    @property
    def period(self) -> EffectivePeriod:
        """The dates on which the rule is in force."""
        ...


DatedT = TypeVar("DatedT", bound=Dated)


def find_for_date(rules: Iterable[DatedT], on_date: date, tax_name: str) -> DatedT:
    """Return the one rule that is in force on ``on_date``.

    Raises:
        NoScheduleForDateError: If no rule is in force on that date.
        TaxError: If more than one rule is in force (the periods overlap).
    """
    matches = [rule for rule in rules if rule.period.contains(on_date)]
    if not matches:
        raise NoScheduleForDateError(tax_name, on_date)
    if len(matches) > 1:
        raise TaxError(f"{len(matches)} {tax_name} schedules overlap on {on_date.isoformat()}.")
    return matches[0]


def make_bands(limits: Sequence[int], rates: Sequence[str]) -> tuple[Band, ...]:
    """Build contiguous bands from band limits and rates.

    Args:
        limits: The upper limits of all bands except the last, in UGX.
        rates: One rate per band, as strings (for example ``"0.2"``).
            ``len(rates)`` must be ``len(limits) + 1``.

    Example:
        ``make_bands([335_000], ["0", "0.2"])`` gives a 0% band to 335,000
        and a 20% band above it.
    """
    if len(rates) != len(limits) + 1:
        raise TaxError("There must be exactly one more rate than limits.")
    lowers = [Money.zero(), *(Money(limit) for limit in limits)]
    uppers: list[Money | None] = [*(Money(limit) for limit in limits), None]
    return tuple(
        Band(lower=lower, upper=upper, rate=Decimal(rate))
        for lower, upper, rate in zip(lowers, uppers, rates)
    )
