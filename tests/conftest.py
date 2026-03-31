"""Fixtures for Eloverblik Custom tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.eloverblik_custom.const import (
    CONF_METERING_POINT,
    CONF_REFRESH_TOKEN,
)

MOCK_REFRESH_TOKEN = "test_refresh_token"
MOCK_METERING_POINT = "571313174200000000"
MOCK_ACCESS_TOKEN = "test_access_token"

MOCK_TIME_SERIES_RESPONSE = {
    "result": [
        {
            "success": True,
            "errorCode": 10000,
            "errorText": "NoError",
            "MyEnergyData_MarketDocument": {
                "TimeSeries": [
                    {
                        "Period": [
                            {
                                "timeInterval": {
                                    "start": "2024-01-01T23:00:00Z",
                                    "end": "2024-01-02T23:00:00Z",
                                },
                                "Point": [
                                    {
                                        "position": "1",
                                        "out_Quantity.quantity": "0.5",
                                    },
                                    {
                                        "position": "2",
                                        "out_Quantity.quantity": "0.3",
                                    },
                                    {
                                        "position": "3",
                                        "out_Quantity.quantity": "0.2",
                                    },
                                ],
                            },
                            {
                                "timeInterval": {
                                    "start": "2024-01-02T23:00:00Z",
                                    "end": "2024-01-03T23:00:00Z",
                                },
                                "Point": [
                                    {
                                        "position": "1",
                                        "out_Quantity.quantity": "0.4",
                                    },
                                    {
                                        "position": "2",
                                        "out_Quantity.quantity": "0.6",
                                    },
                                ],
                            },
                        ]
                    }
                ]
            },
        }
    ]
}


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return {
        CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
        CONF_METERING_POINT: MOCK_METERING_POINT,
    }


@pytest.fixture
def mock_eloverblik_api() -> Generator[AsyncMock]:
    """Mock the Eloverblik API client."""
    with patch(
        "custom_components.eloverblik_custom.api.EloverblikApiClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)
        mock_client.async_get_time_series = AsyncMock(
            return_value=MOCK_TIME_SERIES_RESPONSE
        )
        mock_client.async_get_latest_consumption = AsyncMock(
            return_value={
                "latest_hour": {
                    "api_start_utc": "2024-01-03T00:00:00Z",
                    "api_end_utc": "2024-01-03T01:00:00Z",
                    "start": "2024-01-03T01:00:00+01:00",
                    "end": "2024-01-03T02:00:00+01:00",
                    "kwh": 0.6,
                },
                "latest_hour_kwh": 0.6,
                "window_total_kwh": 2.0,
                "hourly": [
                    {
                        "api_start_utc": "2024-01-01T23:00:00Z",
                        "api_end_utc": "2024-01-02T00:00:00Z",
                        "start": "2024-01-02T00:00:00+01:00",
                        "end": "2024-01-02T01:00:00+01:00",
                        "kwh": 0.5,
                    },
                    {
                        "api_start_utc": "2024-01-02T00:00:00Z",
                        "api_end_utc": "2024-01-02T01:00:00Z",
                        "start": "2024-01-02T01:00:00+01:00",
                        "end": "2024-01-02T02:00:00+01:00",
                        "kwh": 0.3,
                    },
                    {
                        "api_start_utc": "2024-01-02T01:00:00Z",
                        "api_end_utc": "2024-01-02T02:00:00Z",
                        "start": "2024-01-02T02:00:00+01:00",
                        "end": "2024-01-02T03:00:00+01:00",
                        "kwh": 0.2,
                    },
                    {
                        "api_start_utc": "2024-01-02T23:00:00Z",
                        "api_end_utc": "2024-01-03T00:00:00Z",
                        "start": "2024-01-03T00:00:00+01:00",
                        "end": "2024-01-03T01:00:00+01:00",
                        "kwh": 0.4,
                    },
                    {
                        "api_start_utc": "2024-01-03T00:00:00Z",
                        "api_end_utc": "2024-01-03T01:00:00Z",
                        "start": "2024-01-03T01:00:00+01:00",
                        "end": "2024-01-03T02:00:00+01:00",
                        "kwh": 0.6,
                    },
                ],
                "daily": {
                    "2024-01-02": 1.0,
                    "2024-01-03": 1.0,
                },
            }
        )
        yield mock_client
