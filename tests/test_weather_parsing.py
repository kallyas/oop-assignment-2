"""Offline tests of the parsing functions. They use the saved JSON in ``tests/data``."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from conftest import load_sample
from weather.config import build_user_agent
from weather.exceptions import AmbiguousLocationError, ForecastParseError, LocationNotFoundError
from weather.forecast import COL_CODE, COL_PRECIP, COL_TMAX, COL_TMIN, COL_WEATHER, COL_WIND
from weather.forecast import forecast_to_dataframe
from weather.geocoding import choose_location, parse_geocoding_response
from weather.met_norway import COL_HOURS, compare_sources, met_to_daily_dataframe
from weather.weather_codes import describe_weather_code


def test_geocoding_parses_dresden() -> None:
    locations = parse_geocoding_response(load_sample("geocode_dresden.json"))
    first = locations[0]
    assert (first.name, first.country, first.timezone) == ("Dresden", "Germany", "Europe/Berlin")
    assert first.latitude == pytest.approx(51.05, abs=0.01)
    assert first.longitude == pytest.approx(13.74, abs=0.01)


def test_geocoding_without_results_key_gives_empty_list() -> None:
    payload = load_sample("geocode_no_results.json")
    assert "results" not in payload
    assert parse_geocoding_response(payload) == []


def test_ambiguous_name_needs_a_choice() -> None:
    candidates = parse_geocoding_response(load_sample("geocode_springfield.json"))
    assert len(candidates) > 1
    with pytest.raises(AmbiguousLocationError, match="Springfield"):
        choose_location("Springfield", candidates)
    assert choose_location("Springfield", candidates, choice=2) == candidates[1]
    assert choose_location("Springfield", candidates, input_func=lambda _: "3") == candidates[2]
    with pytest.raises(ValueError):
        choose_location("Springfield", candidates, choice=len(candidates) + 1)


def test_no_candidates_raises_location_not_found() -> None:
    with pytest.raises(LocationNotFoundError):
        choose_location("Qwxzzyplort", [])


def test_forecast_dataframe_columns_and_values(forecast_payload: dict[str, Any]) -> None:
    frame = forecast_to_dataframe(forecast_payload)
    assert list(frame.columns) == [COL_WEATHER, COL_TMAX, COL_TMIN, COL_PRECIP, COL_WIND, COL_CODE]
    assert len(frame) == len(forecast_payload["daily"]["time"])
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert frame.index[0] == pd.Timestamp(forecast_payload["daily"]["time"][0])
    assert frame[COL_TMAX].iloc[0] == forecast_payload["daily"]["temperature_2m_max"][0]
    assert (frame[COL_TMAX] >= frame[COL_TMIN]).all()
    assert frame.attrs["timezone"] == "Africa/Kampala"


def test_weather_codes_are_decoded(forecast_payload: dict[str, Any]) -> None:
    frame = forecast_to_dataframe(forecast_payload)
    first_code = forecast_payload["daily"]["weather_code"][0]
    assert frame[COL_WEATHER].iloc[0] == describe_weather_code(first_code)
    assert describe_weather_code(0) == "Clear sky"
    assert describe_weather_code(95) == "Thunderstorm (slight or moderate)"
    assert describe_weather_code(42) == "Unknown code (42)"
    assert describe_weather_code(None) == "No data"


def test_forecast_with_missing_daily_data_raises(forecast_payload: dict[str, Any]) -> None:
    with pytest.raises(ForecastParseError):
        forecast_to_dataframe({"latitude": 0.3})
    broken = dict(forecast_payload, daily={**forecast_payload["daily"]})
    del broken["daily"]["precipitation_sum"]
    with pytest.raises(ForecastParseError, match="precipitation_sum"):
        forecast_to_dataframe(broken)


def test_forecast_with_unexpected_unit_raises(forecast_payload: dict[str, Any]) -> None:
    broken = dict(forecast_payload,
                  daily_units={**forecast_payload["daily_units"], "temperature_2m_max": "°F"})
    with pytest.raises(ForecastParseError, match="°F"):
        forecast_to_dataframe(broken)


def test_met_daily_aggregation(met_payload: dict[str, Any]) -> None:
    daily = met_to_daily_dataframe(met_payload, "Africa/Kampala")
    assert (daily[COL_TMAX] >= daily[COL_TMIN]).all()
    assert (daily[COL_PRECIP] >= 0).all()
    total_hours = sum(
        1 if "next_1_hours" in e["data"] else 6 if "next_6_hours" in e["data"] else 0
        for e in met_payload["properties"]["timeseries"]
    )
    assert daily[COL_HOURS].sum() == total_hours


def test_compare_sources_uses_only_full_days(forecast_payload: dict[str, Any],
                                             met_payload: dict[str, Any]) -> None:
    open_meteo = forecast_to_dataframe(forecast_payload)
    met = met_to_daily_dataframe(met_payload, "Africa/Kampala")
    comparison = compare_sources(open_meteo, met)
    assert not comparison.empty
    assert (met.loc[comparison.index, COL_HOURS] >= 24).all()
    expected = (comparison[f"{COL_TMAX} Open-Meteo"]
                - comparison[f"{COL_TMAX} MET Norway"]).round(1)
    pd.testing.assert_series_equal(comparison[f"{COL_TMAX} difference"], expected,
                                   check_names=False)


def test_user_agent_needs_an_email() -> None:
    assert "student@uni.example" in build_user_agent("student@uni.example")
    with pytest.raises(ValueError):
        build_user_agent("not an email")
