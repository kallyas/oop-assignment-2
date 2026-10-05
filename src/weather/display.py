"""Part B.4: text summary, formatted table and charts."""

from __future__ import annotations

import pandas as pd
from matplotlib.figure import Figure
from pandas.io.formats.style import Styler

from weather.config import MET_NORWAY_CREDIT, OPEN_METEO_CREDIT
from weather.forecast import COL_CODE, COL_PRECIP, COL_TMAX, COL_TMIN, COL_WEATHER, COL_WIND
from weather.geocoding import Location


def summarise_forecast(frame: pd.DataFrame, location: Location) -> str:
    """Return a short text summary of a forecast DataFrame."""
    if frame.empty:
        return f"No forecast data for {location.label}."
    warmest = frame[COL_TMAX].idxmax()
    coolest = frame[COL_TMIN].idxmin()
    wettest = frame[COL_PRECIP].idxmax()
    rainy_days = int((frame[COL_PRECIP] >= 1.0).sum())
    common = frame[COL_WEATHER].mode().iloc[0]
    first, last = frame.index.min(), frame.index.max()
    return "\n".join([
        f"Forecast for {location.label}, {first:%d %b} to {last:%d %b %Y} "
        f"(time zone {frame.attrs.get('timezone', 'unknown')}).",
        f"- Warmest day: {warmest:%a %d %b}, up to {frame.at[warmest, COL_TMAX]:.1f} °C.",
        f"- Coolest night: {coolest:%a %d %b}, down to {frame.at[coolest, COL_TMIN]:.1f} °C.",
        f"- Total precipitation: {frame[COL_PRECIP].sum():.1f} mm; {rainy_days} of "
        f"{len(frame)} days have 1 mm or more. Wettest day: {wettest:%a %d %b} "
        f"({frame.at[wettest, COL_PRECIP]:.1f} mm).",
        f"- Strongest wind: {frame[COL_WIND].max():.1f} km/h.",
        f"- Most common weather: {common.lower()}.",
        f"Source: {OPEN_METEO_CREDIT}.",
    ])


def format_forecast_table(frame: pd.DataFrame, location: Location) -> Styler:
    """Return a formatted table of the forecast for display in a notebook."""
    table = frame.drop(columns=[COL_CODE]).copy()
    table.index = pd.DatetimeIndex(table.index).strftime("%a %d %b")
    return (
        table.style
        .format({COL_TMAX: "{:.1f}", COL_TMIN: "{:.1f}", COL_PRECIP: "{:.1f}", COL_WIND: "{:.1f}"})
        .set_caption(f"Daily forecast for {location.label}. {OPEN_METEO_CREDIT}.")
    )


def plot_forecast(frame: pd.DataFrame, location: Location) -> Figure:
    """Plot the daily temperature range (top panel) and precipitation (bottom panel).

    The two panels share the date axis, so the bars do not hide the temperature lines.
    """
    figure = Figure(figsize=(10, 6), layout="constrained")
    temp_ax, rain_ax = figure.subplots(2, 1, sharex=True, height_ratios=[2, 1])
    dates = frame.index

    temp_ax.fill_between(dates, frame[COL_TMIN], frame[COL_TMAX], color="tab:orange",
                         alpha=0.2, label="Temperature range")
    temp_ax.plot(dates, frame[COL_TMAX], marker="o", color="tab:red", label="Daily maximum")
    temp_ax.plot(dates, frame[COL_TMIN], marker="o", color="tab:blue", label="Daily minimum")
    temp_ax.set_ylabel("Air temperature at 2 m (°C)")
    temp_ax.set_title(f"Daily temperature range and precipitation: {location.label}")
    temp_ax.grid(True, alpha=0.3)
    temp_ax.legend(loc="best", fontsize="small")

    bars = rain_ax.bar(dates, frame[COL_PRECIP], width=0.6, color="tab:blue", alpha=0.6,
                       label="Daily precipitation")
    rain_ax.bar_label(bars, fmt="%.1f", fontsize=8)
    rain_ax.set_ylabel("Precipitation (mm)")
    rain_ax.set_ylim(0, max(5.0, float(frame[COL_PRECIP].max()) * 1.25))
    rain_ax.set_xlabel("Date (local time)")
    rain_ax.set_xticks(dates, [d.strftime("%a\n%d %b") for d in dates])
    rain_ax.grid(True, axis="y", alpha=0.3)
    rain_ax.legend(loc="upper left", fontsize="small")
    figure.supxlabel(OPEN_METEO_CREDIT, fontsize=8, color="grey")
    return figure


def plot_source_comparison(comparison: pd.DataFrame, location: Location) -> Figure:
    """Plot daily maximum and minimum temperature from both sources."""
    figure = Figure(figsize=(10, 4.5), layout="constrained")
    axes = figure.subplots()
    dates = comparison.index
    styles = {"Open-Meteo": "-", "MET Norway": "--"}
    for source, line_style in styles.items():
        axes.plot(dates, comparison[f"{COL_TMAX} {source}"], line_style, marker="o",
                  color="tab:red", label=f"Maximum, {source}")
        axes.plot(dates, comparison[f"{COL_TMIN} {source}"], line_style, marker="s",
                  color="tab:blue", label=f"Minimum, {source}")
    axes.set_xlabel("Date (local time)")
    axes.set_ylabel("Air temperature (°C)")
    axes.set_xticks(dates, [d.strftime("%a %d %b") for d in dates])
    axes.set_title(f"Daily temperature from two sources: {location.label}")
    axes.grid(True, alpha=0.3)
    axes.legend(fontsize="small", ncols=2)
    figure.supxlabel(f"{OPEN_METEO_CREDIT}; {MET_NORWAY_CREDIT}", fontsize=8, color="grey")
    return figure
