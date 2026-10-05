"""Part C: a second forecast source, MET Norway Locationforecast 2.0.

MET Norway sends a time series in UTC: hourly steps for about 2.5 days,
then 6-hour steps. This module turns the series into daily values in the
local time zone, so they can be compared with Open-Meteo.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from weather.config import MET_NORWAY_URL
from weather.exceptions import ForecastParseError
from weather.forecast import COL_PRECIP, COL_TMAX, COL_TMIN, validate_coordinates
from weather.http_client import JsonDict, JsonHttpClient, default_client

COL_HOURS: str = "Hours covered"


def get_met_forecast(latitude: float, longitude: float, *,
                     client: JsonHttpClient | None = None) -> JsonDict:
    """Request the compact Locationforecast for a point.

    The MET terms ask for at most 4 decimals in coordinates (better cache
    use), so the coordinates are rounded.

    Raises:
        InvalidCoordinatesError: If the coordinates are out of range.
        ApiRequestError: If the request fails.
    """
    validate_coordinates(latitude, longitude)
    client = client or default_client()
    return client.get_json(MET_NORWAY_URL, {"lat": round(latitude, 4),
                                            "lon": round(longitude, 4)})


def _step_values(entry: dict[str, Any]) -> tuple[float | None, float, int]:
    """Return (air temperature, precipitation, hours covered) for one time step.

    The precipitation of the next 1 hour is used if it is present. If not,
    the next 6 hours are used. This prevents double counting.
    """
    data = entry["data"]
    temperature = data["instant"]["details"].get("air_temperature")
    for key, hours in (("next_1_hours", 1), ("next_6_hours", 6)):
        if key in data:
            precipitation = float(data[key]["details"].get("precipitation_amount", 0.0))
            return temperature, precipitation, hours
    return temperature, 0.0, 0


def met_to_daily_dataframe(payload: JsonDict, timezone: str) -> pd.DataFrame:
    """Convert a MET Norway time series into daily values in ``timezone``.

    Columns: maximum and minimum temperature (°C) of the instant values,
    precipitation sum (mm), and the number of hours that the steps cover.
    Each step is counted on the local date on which it starts, so a 6-hour
    step that starts late in the evening also covers a few hours of the next
    day. A day with fewer than 24 hours is only partly covered.

    Raises:
        ForecastParseError: If the response does not have the expected structure.
    """
    try:
        series = payload["properties"]["timeseries"]
        rows = [(entry["time"], *_step_values(entry)) for entry in series]
    except (KeyError, TypeError) as error:
        raise ForecastParseError("The MET Norway response has an unexpected structure.") from error
    if not rows:
        raise ForecastParseError("The MET Norway time series is empty.")

    steps = pd.DataFrame(rows, columns=["time", "temperature", "precipitation", "hours"])
    local_times = pd.to_datetime(steps["time"], utc=True).dt.tz_convert(timezone)
    steps["Date"] = local_times.dt.tz_localize(None).dt.normalize()
    daily = steps.groupby("Date").agg(
        **{
            COL_TMAX: pd.NamedAgg(column="temperature", aggfunc="max"),
            COL_TMIN: pd.NamedAgg(column="temperature", aggfunc="min"),
            COL_PRECIP: pd.NamedAgg(column="precipitation", aggfunc="sum"),
            COL_HOURS: pd.NamedAgg(column="hours", aggfunc="sum"),
        }
    )
    daily.attrs["timezone"] = timezone
    daily.attrs["source"] = "MET Norway"
    return daily


def compare_sources(open_meteo: pd.DataFrame, met: pd.DataFrame) -> pd.DataFrame:
    """Join the two daily forecasts on date, for days that MET covers fully (24 hours).

    The result has one column per source and variable, and the difference
    (Open-Meteo minus MET Norway) for each variable.
    """
    full_days = met[met[COL_HOURS] >= 24]
    columns = [COL_TMAX, COL_TMIN, COL_PRECIP]
    joined = open_meteo[columns].join(full_days[columns], how="inner",
                                      lsuffix=" Open-Meteo", rsuffix=" MET Norway")
    for column in columns:
        joined[f"{column} difference"] = (
            joined[f"{column} Open-Meteo"] - joined[f"{column} MET Norway"]
        ).round(1)
    return joined
