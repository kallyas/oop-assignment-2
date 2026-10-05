"""WMO weather interpretation codes, as listed in the Open-Meteo forecast documentation."""

from __future__ import annotations

from typing import Final

WMO_WEATHER_CODES: Final[dict[int, str]] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm (slight or moderate)",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def describe_weather_code(code: int | None) -> str:
    """Return a readable description of a WMO code.

    A missing code gives ``"No data"``. A code that is not in the table gives
    ``"Unknown code (N)"``, so the table never fails on new codes.
    """
    if code is None:
        return "No data"
    return WMO_WEATHER_CODES.get(int(code), f"Unknown code ({code})")
