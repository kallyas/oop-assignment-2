"""Shared test helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings

DATA_DIR = Path(__file__).parent / "data"

# Reproducibility: Hypothesis uses a fixed seed, so every run tests the same examples.
settings.register_profile("reproducible", derandomize=True, max_examples=300)
settings.load_profile("reproducible")


def load_sample(name: str) -> dict[str, Any]:
    """Load a saved JSON response from ``tests/data``."""
    with (DATA_DIR / name).open(encoding="utf-8") as file:
        payload: dict[str, Any] = json.load(file)
    return payload


@pytest.fixture
def forecast_payload() -> dict[str, Any]:
    """A saved Open-Meteo daily forecast for Kampala."""
    return load_sample("forecast_kampala.json")


@pytest.fixture
def met_payload() -> dict[str, Any]:
    """A saved MET Norway compact forecast for Kampala."""
    return load_sample("met_kampala.json")
