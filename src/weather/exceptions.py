"""Custom exceptions for the weather client.

Every error that the package raises on purpose is a subclass of ``WeatherError``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weather.geocoding import Location


class WeatherError(Exception):
    """Base class for all weather client errors."""


class ApiRequestError(WeatherError):
    """Raised when an HTTP request fails and no more retries are allowed.

    Attributes:
        url: The URL of the request.
        attempts: How many attempts were made.
        status_code: The last HTTP status code, if the server replied.
        reason: The error reason that the API sent, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        url: str,
        attempts: int,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None:
        self.url = url
        self.attempts = attempts
        self.status_code = status_code
        self.reason = reason
        details = [f"url={url}", f"attempts={attempts}"]
        if status_code is not None:
            details.append(f"status={status_code}")
        if reason:
            details.append(f"reason={reason!r}")
        super().__init__(f"{message} ({', '.join(details)})")


class InvalidCoordinatesError(WeatherError, ValueError):
    """Raised when a latitude, longitude or number of days is out of range."""


class LocationNotFoundError(WeatherError, LookupError):
    """Raised when the geocoding API finds no place for a name."""


class AmbiguousLocationError(WeatherError):
    """Raised when a name matches many places and no choice was given."""

    def __init__(self, name: str, candidates: Sequence[Location]) -> None:
        self.name = name
        self.candidates = tuple(candidates)
        listing = "\n".join(f"  {i}. {c.label}" for i, c in enumerate(self.candidates, start=1))
        super().__init__(
            f"{len(self.candidates)} places match {name!r}. Choose one by number:\n{listing}"
        )


class ForecastParseError(WeatherError, ValueError):
    """Raised when an API response does not have the expected structure."""
