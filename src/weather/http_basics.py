"""Part A: the same geocoding call with ``urllib`` and with ``requests``.

These two functions are for comparison only. The rest of the package uses
``JsonHttpClient``.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

import requests

from weather.config import GEOCODING_URL
from weather.http_client import JsonDict


@dataclass(frozen=True)
class ResponseInfo:
    """Facts about one HTTP response, for Part A.4."""

    url: str
    status_code: int
    content_type: str
    elapsed_ms: float
    body: JsonDict


def geocode_with_urllib(name: str, user_agent: str, count: int = 5,
                        timeout: float = 10.0) -> ResponseInfo:
    """Geocode ``name`` with only ``urllib.request``, ``urllib.parse`` and ``json``.

    The query string is built with ``urllib.parse.urlencode``.
    """
    query = urllib.parse.urlencode({"name": name, "count": count, "language": "en",
                                    "format": "json"})
    url = f"{GEOCODING_URL}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        status = int(response.status)
        content_type = str(response.headers.get("Content-Type", ""))
    elapsed_ms = (time.perf_counter() - start) * 1000
    # The response is bytes. We must decode it ourselves (Open-Meteo sends UTF-8).
    body: JsonDict = json.loads(raw.decode("utf-8"))
    return ResponseInfo(url=url, status_code=status, content_type=content_type,
                        elapsed_ms=elapsed_ms, body=body)


def geocode_with_requests(name: str, user_agent: str, count: int = 5,
                          timeout: float = 10.0) -> ResponseInfo:
    """Geocode ``name`` with ``requests``, the ``params=`` argument and a timeout."""
    params: dict[str, str | int] = {"name": name, "count": count, "language": "en",
                                    "format": "json"}
    response = requests.get(
        GEOCODING_URL,
        params=params,
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    body: JsonDict = response.json()
    return ResponseInfo(url=response.url, status_code=response.status_code,
                        content_type=response.headers.get("Content-Type", ""),
                        elapsed_ms=response.elapsed.total_seconds() * 1000, body=body)
