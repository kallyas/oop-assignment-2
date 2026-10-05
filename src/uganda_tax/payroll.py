"""The monthly payroll pipeline: LST, PAYE, NSSF and net pay.

Order of deductions
-------------------
1. **Total gross** = gross pay + allowances.
2. **Local Service Tax** (if enabled). LST is an allowable deduction for PAYE,
   so it must be known before PAYE.
3. **PAYE** on ``total gross - LST``.
4. **NSSF** employee 5% and employer 10% of total gross. Employee NSSF does
   not reduce the PAYE base, so this step can come after PAYE.
5. **Net pay** = total gross - LST - PAYE - employee NSSF.

The employer NSSF share is not taken from the employee. It is added to the
total cost of employment.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from uganda_tax.base import TaxResult
from uganda_tax.context import TaxContext
from uganda_tax.contributions import LocalServiceTax, NssfContribution
from uganda_tax.money import Money
from uganda_tax.paye import PayeTax


@dataclass(frozen=True)
class Payslip:
    """The result of the payroll pipeline for one employee and one month."""

    total_gross: Money
    lst: TaxResult | None
    paye: TaxResult
    nssf_employee: TaxResult
    nssf_employer: TaxResult

    @property
    def lst_amount(self) -> Money:
        """The LST deducted this month (0 if LST is not enabled)."""
        return self.lst.amount if self.lst is not None else Money.zero()

    @property
    def total_deductions(self) -> Money:
        """All deductions from the employee: LST, PAYE and employee NSSF."""
        return self.lst_amount + self.paye.amount + self.nssf_employee.amount

    @property
    def net_pay(self) -> Money:
        """The amount paid to the employee."""
        return self.total_gross - self.total_deductions

    @property
    def employer_cost(self) -> Money:
        """Total gross plus the employer NSSF contribution."""
        return self.total_gross + self.nssf_employer.amount

    def as_rows(self) -> list[tuple[str, Money]]:
        """Return the payslip as ``(label, amount)`` rows in deduction order."""
        return [
            ("Total gross pay", self.total_gross),
            ("Local Service Tax", self.lst_amount),
            ("PAYE chargeable income", self.paye.taxable_base),
            ("PAYE", self.paye.amount),
            ("NSSF employee (5%)", self.nssf_employee.amount),
            ("Net pay", self.net_pay),
            ("NSSF employer (10%)", self.nssf_employer.amount),
            ("Total employer cost", self.employer_cost),
        ]

    def __str__(self) -> str:
        return "\n".join(f"{label:<24}{str(amount):>18}" for label, amount in self.as_rows())


class Payroll:
    """Runs the deductions in the documented order.

    The pipeline is built by composition: it holds one object for each
    deduction, so each part can be changed or tested on its own.
    """

    def __init__(
        self,
        paye: PayeTax | None = None,
        nssf_employee: NssfContribution | None = None,
        nssf_employer: NssfContribution | None = None,
        lst: LocalServiceTax | None = None,
    ) -> None:
        """Create a payroll pipeline.

        Args:
            paye: The PAYE calculator. Default: official schedules.
            nssf_employee: The employee NSSF contribution. Default: 5%.
            nssf_employer: The employer NSSF contribution. Default: 10%.
            lst: The Local Service Tax calculator. ``None`` turns LST off.
        """
        self.paye = paye or PayeTax()
        self.nssf_employee = nssf_employee or NssfContribution.employee()
        self.nssf_employer = nssf_employer or NssfContribution.employer()
        self.lst = lst

    def run(self, ctx: TaxContext) -> Payslip:
        """Run the pipeline for one month.

        Raises:
            MissingContextDataError: If the context has no employment income.
            NoScheduleForDateError: If no PAYE schedule is in force.
        """
        employment = ctx.require_employment()
        lst_result = self.lst.calculate(ctx) if self.lst is not None else None
        lst_amount = lst_result.amount if lst_result is not None else Money.zero()

        paye_ctx = replace(
            ctx,
            employment=replace(
                employment,
                deductions_before_paye=employment.deductions_before_paye + lst_amount,
            ),
        )
        return Payslip(
            total_gross=employment.total_gross,
            lst=lst_result,
            paye=self.paye.calculate(paye_ctx),
            nssf_employee=self.nssf_employee.calculate(ctx),
            nssf_employer=self.nssf_employer.calculate(ctx),
        )
