"""Endpoints and the User-Agent header.

The contact email is never written in shared code. It comes from the
``WEATHER_CONTACT_EMAIL`` environment variable or from the notebook
configuration cell.
"""

from __future__ import annotations

import os
from typing import Final

GEOCODING_URL: Final = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL: Final = "https://api.open-meteo.com/v1/forecast"
MET_NORWAY_URL: Final = "https://api.met.no/weatherapi/locationforecast/2.0/compact"

APP_NAME: Final = "ucu-oop-assignment2-weather/1.0"
CONTACT_EMAIL_ENV: Final = "WEATHER_CONTACT_EMAIL"
#: A clear placeholder. The ``.example`` domain is reserved and is never a real address.
PLACEHOLDER_EMAIL: Final = "CHANGE-ME@university.example"

OPEN_METEO_CREDIT: Final = "Weather data by Open-Meteo.com (CC BY 4.0)"
MET_NORWAY_CREDIT: Final = "Data from MET Norway (CC BY 4.0 / NLOD 2.0)"


def contact_email(default: str = PLACEHOLDER_EMAIL) -> str:
    """Return the contact email from the environment, or ``default``."""
    return os.environ.get(CONTACT_EMAIL_ENV, "").strip() or default


def build_user_agent(email: str) -> str:
    """Return a User-Agent value that names the app and gives a contact email.

    MET Norway's terms of service require this header.

    Raises:
        ValueError: If ``email`` does not look like an email address.
    """
    email = email.strip()
    if "@" not in email or " " in email:
        raise ValueError(f"{email!r} is not a valid contact email.")
    return f"{APP_NAME} (contact: {email})"
