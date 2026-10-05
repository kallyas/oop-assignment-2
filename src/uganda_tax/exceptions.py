"""Custom exception hierarchy for the Uganda tax engine.

All errors raised on purpose by the engine are subclasses of ``TaxError``.
Callers can catch ``TaxError`` to handle every engine failure in one place.
"""

from __future__ import annotations

from datetime import date


class TaxError(Exception):
    """Base class for all tax engine errors."""


class InvalidAmountError(TaxError, ValueError):
    """Raised when a value cannot be used as a ``Money`` amount."""


class InvalidIncomeError(TaxError, ValueError):
    """Raised when an income or other input amount is not valid (for example, negative)."""


class MissingContextDataError(TaxError):
    """Raised when a ``TaxContext`` does not hold the data that a tax needs."""


class NoScheduleForDateError(TaxError, LookupError):
    """Raised when no rate schedule applies on the requested date."""

    def __init__(self, tax_name: str, on_date: date, detail: str = "") -> None:
        self.tax_name = tax_name
        self.on_date = on_date
        message = f"No {tax_name} schedule applies on {on_date.isoformat()}."
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)


class NoWithholdingRuleError(TaxError, LookupError):
    """Raised when no withholding tax rule exists for a payment type and payee residency."""
