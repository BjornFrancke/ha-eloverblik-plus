"""HTTP-level tests for the Eloverblik API client."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest

from custom_components.eloverblik_custom.api import (
    EloverblikApiClient,
    EloverblikAuthError,
    EloverblikConnectionError,
)
from custom_components.eloverblik_custom.const import API_METER_DATA_URL, API_TOKEN_URL


class MockResponse:
    """Minimal aiohttp response mock for async context manager usage."""

    def __init__(
        self,
        *,
        status: int,
        json_data: dict | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self.status = status
        self._json_data = json_data or {}
        self._raise_error = raise_error

    async def __aenter__(self) -> MockResponse:
        """Return the mocked response."""
        return self

    async def __aexit__(self, *_args: object) -> bool:
        """Do not suppress exceptions."""
        return False

    async def json(self) -> dict:
        """Return the configured JSON payload."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise a configured HTTP error when asked."""
        if self._raise_error is not None:
            raise self._raise_error


@pytest.fixture
def api_client() -> tuple[EloverblikApiClient, MagicMock]:
    """Create an API client with a mocked aiohttp session."""
    session = MagicMock()
    client = EloverblikApiClient(session, "refresh_token", "571313174200318497")
    return client, session


async def test_async_get_access_token_success(
    api_client: tuple[EloverblikApiClient, MagicMock],
) -> None:
    """Test successful token exchange."""
    client, session = api_client
    session.get.return_value = MockResponse(status=200, json_data={"result": "access"})

    access_token = await client.async_get_access_token()

    assert access_token == "access"
    session.get.assert_called_once_with(
        API_TOKEN_URL, headers={"Authorization": "Bearer refresh_token"}
    )


async def test_async_get_access_token_invalid_token(
    api_client: tuple[EloverblikApiClient, MagicMock],
) -> None:
    """Test auth failures during token exchange."""
    client, session = api_client
    session.get.return_value = MockResponse(status=401)

    with pytest.raises(EloverblikAuthError, match="Invalid refresh token"):
        await client.async_get_access_token()


async def test_async_get_access_token_connection_error(
    api_client: tuple[EloverblikApiClient, MagicMock],
) -> None:
    """Test connection errors during token exchange."""
    client, session = api_client
    session.get.side_effect = aiohttp.ClientError("network down")

    with pytest.raises(EloverblikConnectionError, match="network down"):
        await client.async_get_access_token()


async def test_async_get_time_series_success(
    api_client: tuple[EloverblikApiClient, MagicMock],
) -> None:
    """Test successful time-series fetch."""
    client, session = api_client
    payload = {"result": [{"success": True, "errorCode": 10000}]}
    session.post.return_value = MockResponse(status=200, json_data=payload)

    result = await client.async_get_time_series(
        "access_token",
        start_date="2026-03-21",
        end_date="2026-03-31",
    )

    assert result == payload
    session.post.assert_called_once_with(
        f"{API_METER_DATA_URL}/2026-03-21/2026-03-31/Hour",
        headers={
            "Authorization": "Bearer access_token",
            "Content-Type": "application/json",
        },
        json={"meteringPoints": {"meteringPoint": ["571313174200318497"]}},
    )


async def test_async_get_time_series_invalid_access_token(
    api_client: tuple[EloverblikApiClient, MagicMock],
) -> None:
    """Test auth failures during time-series fetch."""
    client, session = api_client
    session.post.return_value = MockResponse(status=401)

    with pytest.raises(EloverblikAuthError, match="Access token expired or invalid"):
        await client.async_get_time_series("access_token")


async def test_async_get_time_series_connection_error(
    api_client: tuple[EloverblikApiClient, MagicMock],
) -> None:
    """Test connection errors during time-series fetch."""
    client, session = api_client
    session.post.side_effect = aiohttp.ClientError("network down")

    with pytest.raises(EloverblikConnectionError, match="network down"):
        await client.async_get_time_series("access_token")
