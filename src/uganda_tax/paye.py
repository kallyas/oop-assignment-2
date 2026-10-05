"""Pay As You Earn (PAYE) on monthly employment income."""

from __future__ import annotations

from collections.abc import Iterable

from uganda_tax.base import Tax, TaxResult
from uganda_tax.context import TaxContext
from uganda_tax.money import Money
from uganda_tax.rates import DEFAULT_PAYE_SCHEDULES
from uganda_tax.schedules import ProgressiveSchedule, find_for_date


class PayeTax(Tax):
    """Monthly PAYE for resident and non-resident employees.

    The chargeable income is ``gross pay + allowances - deductions before PAYE``.
    The class selects the schedule by the residency and the date in the context.
    """

    name = "PAYE"

    def __init__(self, schedules: Iterable[ProgressiveSchedule] = DEFAULT_PAYE_SCHEDULES) -> None:
        """Create a PAYE calculator.

        Args:
            schedules: The PAYE schedules to choose from. The default is the
                official URA scales in ``uganda_tax.rates``.
        """
        self._schedules: tuple[ProgressiveSchedule, ...] = tuple(schedules)

    def schedule_for(self, ctx: TaxContext) -> ProgressiveSchedule:
        """Return the schedule for the residency and date in ``ctx``.

        Raises:
            NoScheduleForDateError: If no schedule for that residency is in force.
        """
        same_residency = (s for s in self._schedules if s.residency is ctx.residency)
        return find_for_date(same_residency, ctx.on_date, f"{ctx.residency.value} PAYE")

    def chargeable_income(self, ctx: TaxContext) -> Money:
        """Return the monthly chargeable income (never below 0)."""
        employment = ctx.require_employment()
        return (employment.total_gross - employment.deductions_before_paye).clamp_at_zero()

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Calculate monthly PAYE.

        Raises:
            MissingContextDataError: If the context has no employment income.
            NoScheduleForDateError: If no schedule is in force on ``ctx.on_date``.
        """
        schedule = self.schedule_for(ctx)
        income = self.chargeable_income(ctx)
        lines = schedule.lines_for(income)
        return TaxResult(
            tax_name=self.name,
            taxable_base=income,
            amount=sum((line.amount for line in lines), Money.zero()),
            lines=lines,
            notes=(f"Schedule: {schedule.name} ({schedule.period}).", f"Source: {schedule.source}."),
        )
