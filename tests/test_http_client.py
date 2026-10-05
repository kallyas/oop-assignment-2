"""Offline tests of the retry logic. A mock session replaces the network."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from conftest import load_sample
from weather.exceptions import ApiRequestError, InvalidCoordinatesError
from weather.forecast import get_forecast
from weather.http_client import JsonHttpClient, RetryPolicy

URL = "https://api.example/test"


def make_response(status: int, body: Any) -> requests.Response:
    """Build a ``requests.Response`` without a network call."""
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode("utf-8")
    response.url = URL
    response.headers["Content-Type"] = "application/json"
    return response


def make_client(*outcomes: object) -> tuple[JsonHttpClient, Mock, list[float]]:
    """Return a client whose session returns or raises ``outcomes`` in order."""
    session = Mock(spec=requests.Session)
    session.get.side_effect = list(outcomes)
    waits: list[float] = []
    client = JsonHttpClient("test-agent (contact: test@uni.example)", session=session,
                            sleep=waits.append, retry=RetryPolicy(max_attempts=3))
    return client, session, waits


def test_success_returns_json_and_sends_user_agent() -> None:
    client, session, waits = make_client(make_response(200, {"ok": True}))
    assert client.get_json(URL, {"a": 1}) == {"ok": True}
    _, kwargs = session.get.call_args
    assert kwargs["headers"]["User-Agent"].startswith("test-agent")
    assert kwargs["timeout"] == 10.0
    assert waits == []


def test_server_error_is_retried_with_exponential_backoff() -> None:
    client, session, waits = make_client(
        make_response(503, {}), requests.ConnectionError("down"), make_response(200, {"ok": 1})
    )
    assert client.get_json(URL) == {"ok": 1}
    assert session.get.call_count == 3
    assert waits == [0.5, 1.0]


def test_final_failure_raises_custom_error_after_retry_cap() -> None:
    client, session, _ = make_client(*[requests.Timeout("slow")] * 3)
    with pytest.raises(ApiRequestError) as caught:
        client.get_json(URL)
    assert caught.value.attempts == 3
    assert session.get.call_count == 3
    assert isinstance(caught.value.__cause__, requests.Timeout)


def test_client_error_is_not_retried_and_reason_is_kept() -> None:
    body = load_sample("forecast_error_invalid_latitude.json")   # real HTTP 400 body
    client, session, _ = make_client(make_response(400, body))
    with pytest.raises(ApiRequestError) as caught:
        client.get_json(URL)
    assert caught.value.status_code == 400
    assert caught.value.reason is not None and "Latitude" in caught.value.reason
    assert session.get.call_count == 1


def test_cache_prevents_a_second_request() -> None:
    client, session, _ = make_client(make_response(200, {"n": 1}))
    assert client.get_json(URL, {"x": 1}) == client.get_json(URL, {"x": 1})
    assert session.get.call_count == 1


def test_backoff_is_capped() -> None:
    policy = RetryPolicy(backoff_base=1, backoff_factor=10, max_backoff=5)
    assert [policy.delay_for(n) for n in (1, 2, 3)] == [1, 5, 5]


def test_invalid_latitude_is_rejected_before_any_request() -> None:
    client, session, _ = make_client()
    with pytest.raises(InvalidCoordinatesError):
        get_forecast(999, 0, client=client)
    session.get.assert_not_called()
