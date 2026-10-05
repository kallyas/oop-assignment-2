"""Part B.1: place name to coordinates with the Open-Meteo Geocoding API."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from weather.config import GEOCODING_URL
from weather.exceptions import AmbiguousLocationError, ForecastParseError, LocationNotFoundError
from weather.http_client import JsonDict, JsonHttpClient, default_client


@dataclass(frozen=True)
class Location:
    """One candidate place from the geocoding API."""

    name: str
    latitude: float
    longitude: float
    country: str = ""
    admin1: str = ""
    timezone: str = ""
    population: int | None = None

    @property
    def label(self) -> str:
        """A readable label, for example ``"Dresden, Saxony, Germany (51.0509, 13.7383)"``."""
        parts = [part for part in (self.name, self.admin1, self.country) if part]
        return f"{', '.join(parts)} ({self.latitude:.4f}, {self.longitude:.4f})"


def _location_from_result(result: dict[str, Any]) -> Location:
    try:
        return Location(
            name=str(result["name"]),
            latitude=float(result["latitude"]),
            longitude=float(result["longitude"]),
            country=str(result.get("country", "")),
            admin1=str(result.get("admin1", "")),
            timezone=str(result.get("timezone", "")),
            population=int(result["population"]) if "population" in result else None,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ForecastParseError(f"Bad geocoding result: {result!r}") from error


def parse_geocoding_response(payload: JsonDict) -> list[Location]:
    """Convert a geocoding response into a list of ``Location`` objects.

    The API leaves out the ``results`` key when nothing matches, so a missing
    key gives an empty list.
    """
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ForecastParseError("'results' must be a list.")
    return [_location_from_result(result) for result in results]


def geocode(name: str, count: int = 10, *, client: JsonHttpClient | None = None) -> list[Location]:
    """Return the candidate locations for ``name`` (an empty list if none match).

    Args:
        name: A place name, for example ``"Dresden"``.
        count: The largest number of candidates to return (1 to 100).
        client: The HTTP client to use. Default: ``default_client()``.
    """
    name = name.strip()
    if not name:
        raise LocationNotFoundError("The location name is empty.")
    if not 1 <= count <= 100:
        raise ValueError("count must be from 1 to 100.")
    client = client or default_client()
    payload = client.get_json(GEOCODING_URL, {"name": name, "count": count,
                                              "language": "en", "format": "json"})
    return parse_geocoding_response(payload)


def choose_location(
    name: str,
    candidates: Sequence[Location],
    choice: int | None = None,
    input_func: Callable[[str], str] | None = None,
) -> Location:
    """Select one location from the candidates.

    Args:
        name: The name that the user searched for (used in messages).
        candidates: The result of ``geocode``.
        choice: A 1-based number from the candidate list. Use this in the
            notebook configuration cell so that "Run All" needs no input.
        input_func: If given and ``choice`` is ``None``, ask the user with this
            function (for example the built-in ``input``).

    Raises:
        LocationNotFoundError: If there are no candidates.
        AmbiguousLocationError: If there are many candidates and no choice.
        ValueError: If ``choice`` is not a number in the list.
    """
    if not candidates:
        raise LocationNotFoundError(f"No place matches {name!r}.")
    if choice is None and input_func is not None and len(candidates) > 1:
        print(AmbiguousLocationError(name, candidates))
        answer = input_func(f"Number (1-{len(candidates)}): ").strip()
        if not answer.isdigit():
            raise ValueError(f"{answer!r} is not a number.")
        choice = int(answer)
    if choice is None:
        if len(candidates) == 1:
            return candidates[0]
        raise AmbiguousLocationError(name, candidates)
    if not 1 <= choice <= len(candidates):
        raise ValueError(f"Choice {choice} is not from 1 to {len(candidates)}.")
    return candidates[choice - 1]
