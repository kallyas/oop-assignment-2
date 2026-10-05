"""Part B.2 and B.3: get a daily forecast from Open-Meteo and convert it to a DataFrame."""

from __future__ import annotations

from typing import Final

import pandas as pd

from weather.config import OPEN_METEO_FORECAST_URL
from weather.exceptions import ForecastParseError, InvalidCoordinatesError
from weather.http_client import JsonDict, JsonHttpClient, default_client
from weather.weather_codes import describe_weather_code

DAILY_VARIABLES: Final = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
)
MAX_FORECAST_DAYS: Final = 16

# Column names of the forecast DataFrame. The unit is part of each name.
COL_WEATHER: Final = "Weather"
COL_CODE: Final = "WMO code"
COL_TMAX: Final = "Max temperature (°C)"
COL_TMIN: Final = "Min temperature (°C)"
COL_PRECIP: Final = "Precipitation (mm)"
COL_WIND: Final = "Max wind speed (km/h)"

#: API variable -> (column name, unit that the column name states).
_COLUMNS: Final[dict[str, tuple[str, str]]] = {
    "temperature_2m_max": (COL_TMAX, "°C"),
    "temperature_2m_min": (COL_TMIN, "°C"),
    "precipitation_sum": (COL_PRECIP, "mm"),
    "wind_speed_10m_max": (COL_WIND, "km/h"),
}


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Raise ``InvalidCoordinatesError`` if the coordinates are out of range."""
    if not -90.0 <= latitude <= 90.0:
        raise InvalidCoordinatesError(f"Latitude {latitude} must be from -90 to 90.")
    if not -180.0 <= longitude <= 180.0:
        raise InvalidCoordinatesError(f"Longitude {longitude} must be from -180 to 180.")


def get_forecast(latitude: float, longitude: float, days: int = 7, *,
                 client: JsonHttpClient | None = None) -> JsonDict:
    """Request a daily forecast from Open-Meteo.

    The request asks for the WMO weather code, maximum and minimum
    temperature, precipitation sum, and maximum wind speed.
    ``timezone=auto`` makes the dates match the local time of the location.

    Args:
        latitude: Latitude in degrees (-90 to 90).
        longitude: Longitude in degrees (-180 to 180).
        days: Number of forecast days (1 to 16).
        client: The HTTP client. Default: ``default_client()``.

    Raises:
        InvalidCoordinatesError: If an input is out of range.
        ApiRequestError: If the request fails.
    """
    validate_coordinates(latitude, longitude)
    if not 1 <= days <= MAX_FORECAST_DAYS:
        raise InvalidCoordinatesError(f"days must be from 1 to {MAX_FORECAST_DAYS}, not {days}.")
    client = client or default_client()
    return client.get_json(OPEN_METEO_FORECAST_URL, {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto",
        "forecast_days": days,
    })


def forecast_to_dataframe(payload: JsonDict) -> pd.DataFrame:
    """Convert an Open-Meteo daily forecast into a DataFrame.

    The index is the local date. Column names include the units. The
    function checks that the units in the response are the units in the
    column names.

    Raises:
        ForecastParseError: If a key is missing, the lists have different
            lengths, or a unit is not the expected unit.
    """
    daily = payload.get("daily")
    units = payload.get("daily_units", {})
    if not isinstance(daily, dict) or "time" not in daily:
        raise ForecastParseError("The response has no 'daily' data.")
    missing = [name for name in DAILY_VARIABLES if name not in daily]
    if missing:
        raise ForecastParseError(f"The response has no data for: {', '.join(missing)}.")
    length = len(daily["time"])
    if any(len(daily[name]) != length for name in DAILY_VARIABLES):
        raise ForecastParseError("The daily lists do not have the same length.")
    for variable, (_, expected_unit) in _COLUMNS.items():
        if units.get(variable, expected_unit) != expected_unit:
            raise ForecastParseError(
                f"Expected {variable} in {expected_unit}, but got {units.get(variable)}."
            )

    codes = [None if code is None else int(code) for code in daily["weather_code"]]
    frame = pd.DataFrame(
        {
            COL_WEATHER: [describe_weather_code(code) for code in codes],
            **{column: pd.Series(daily[variable], dtype="float64").to_numpy()
               for variable, (column, _) in _COLUMNS.items()},
            COL_CODE: pd.array(codes, dtype="Int64"),
        },
        index=pd.DatetimeIndex(daily["time"], name="Date"),
    )
    frame.attrs["timezone"] = str(payload.get("timezone", ""))
    frame.attrs["source"] = "Open-Meteo"
    return frame
