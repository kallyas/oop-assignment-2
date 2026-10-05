"""A JSON HTTP client with timeout, retries, exponential backoff and a small cache.

Every API call in the package goes through ``JsonHttpClient.get_json``.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Union

import requests

from weather.config import build_user_agent, contact_email
from weather.exceptions import ApiRequestError

JsonDict = dict[str, Any]
ParamValue = Union[str, int, float]
Params = Mapping[str, ParamValue]
#: Called before each retry with (attempt number, delay in seconds, reason).
RetryCallback = Callable[[int, float, str], None]


@dataclass(frozen=True)
class RetryPolicy:
    """When to retry a request, and how long to wait.

    Attributes:
        max_attempts: Total number of attempts, including the first one (the retry cap).
        backoff_base: Wait before the first retry, in seconds.
        backoff_factor: The wait is multiplied by this value after each retry.
        max_backoff: The longest wait between two attempts, in seconds.
        retry_statuses: HTTP status codes that are retried (5xx and 429).
    """

    max_attempts: int = 4
    backoff_base: float = 0.5
    backoff_factor: float = 2.0
    max_backoff: float = 8.0
    retry_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be 1 or more.")
        if self.backoff_base < 0 or self.backoff_factor < 1 or self.max_backoff < 0:
            raise ValueError("Backoff values must not be negative, and the factor must be 1 or more.")

    def delay_for(self, attempt: int) -> float:
        """Return the wait in seconds after failed attempt number ``attempt`` (1-based)."""
        return float(min(self.max_backoff, self.backoff_base * self.backoff_factor ** (attempt - 1)))


def api_error_reason(response: requests.Response) -> str | None:
    """Return the ``reason`` text from an Open-Meteo error body, if there is one."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200] or None
    if isinstance(body, dict) and isinstance(body.get("reason"), str):
        return str(body["reason"])
    return None


class JsonHttpClient:
    """Sends GET requests and returns JSON objects.

    * Each request has a timeout.
    * ``raise_for_status()`` is called on each response.
    * Connection errors, timeouts, 5xx and 429 responses are retried with
      exponential backoff, up to ``RetryPolicy.max_attempts``.
    * Other 4xx responses are not retried, because a retry gives the same result.
    * On final failure, ``ApiRequestError`` is raised.
    * Successful responses are cached in memory to keep traffic low.
    """

    def __init__(
        self,
        user_agent: str,
        *,
        timeout: float = 10.0,
        retry: RetryPolicy | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        on_retry: RetryCallback | None = None,
        use_cache: bool = True,
    ) -> None:
        """Create a client.

        Args:
            user_agent: The User-Agent header value (app name and contact email).
            timeout: Timeout for each attempt, in seconds.
            retry: The retry policy. Default: ``RetryPolicy()``.
            session: The ``requests`` session. Tests can give a fake session.
            sleep: The function used to wait. Tests can give a function that does not wait.
            on_retry: Optional function that is called before each retry.
            use_cache: If ``True``, keep successful responses in memory.
        """
        if timeout <= 0:
            raise ValueError("timeout must be more than 0 seconds.")
        self.user_agent = user_agent
        self.timeout = timeout
        self.retry = retry or RetryPolicy()
        self.session = session or requests.Session()
        self._sleep = sleep
        self._on_retry = on_retry
        self._cache: dict[tuple[str, tuple[tuple[str, str], ...]], JsonDict] | None = (
            {} if use_cache else None
        )

    def _wait_before_retry(self, attempt: int, reason: str) -> None:
        delay = self.retry.delay_for(attempt)
        if self._on_retry is not None:
            self._on_retry(attempt, delay, reason)
        self._sleep(delay)

    def get_json(self, url: str, params: Params | None = None) -> JsonDict:
        """Send a GET request and return the JSON object in the response.

        Raises:
            ApiRequestError: If all attempts fail, the server sends a 4xx
                error, or the body is not a JSON object.
        """
        params = dict(params or {})
        cache_key = (url, tuple(sorted((key, str(value)) for key, value in params.items())))
        if self._cache is not None and cache_key in self._cache:
            return self._cache[cache_key]

        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        attempts = self.retry.max_attempts
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.get(url, params=params, headers=headers,
                                            timeout=self.timeout)
                response.raise_for_status()
            except requests.HTTPError as error:
                status = error.response.status_code if error.response is not None else None
                reason = api_error_reason(error.response) if error.response is not None else None
                if status in self.retry.retry_statuses and attempt < attempts:
                    self._wait_before_retry(attempt, f"HTTP {status}")
                    continue
                raise ApiRequestError("The API returned an error", url=url, attempts=attempt,
                                      status_code=status, reason=reason) from error
            except (requests.ConnectionError, requests.Timeout) as error:
                if attempt < attempts:
                    self._wait_before_retry(attempt, type(error).__name__)
                    continue
                raise ApiRequestError(f"Request failed: {type(error).__name__}", url=url,
                                      attempts=attempt) from error

            try:
                body = response.json()
            except ValueError as error:
                raise ApiRequestError("The response is not valid JSON", url=url,
                                      attempts=attempt, status_code=response.status_code) from error
            if not isinstance(body, dict):
                raise ApiRequestError("The response is not a JSON object", url=url,
                                      attempts=attempt, status_code=response.status_code)
            if self._cache is not None:
                self._cache[cache_key] = body
            return body
        raise AssertionError("not reached")  # The loop always returns or raises.


def default_client() -> JsonHttpClient:
    """Return a client whose User-Agent uses the ``WEATHER_CONTACT_EMAIL`` variable."""
    return JsonHttpClient(build_user_agent(contact_email()))
