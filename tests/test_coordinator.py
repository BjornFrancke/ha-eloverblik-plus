"""Tests for the Eloverblik data coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.eloverblik_custom.api import (
    EloverblikAuthError,
    EloverblikConnectionError,
)
from custom_components.eloverblik_custom.coordinator import (
    EloverblikDataUpdateCoordinator,
)


async def test_coordinator_returns_latest_consumption(hass) -> None:
    """Test successful coordinator refresh."""
    client = AsyncMock()
    client.metering_point = "571313174200318497"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": {
            "start": "2024-01-02T00:00:00+01:00",
            "end": "2024-01-02T01:00:00+01:00",
            "kwh": 1.23,
        },
        "latest_hour_kwh": 1.23,
        "window_total_kwh": 1.23,
        "hourly": [
            {
                "start": "2024-01-02T00:00:00+01:00",
                "end": "2024-01-02T01:00:00+01:00",
                "kwh": 1.23,
            }
        ],
        "daily": {"2024-01-02": 1.23},
    }
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    result = await coordinator._async_update_data()

    assert result["latest_hour_kwh"] == 1.23


async def test_coordinator_maps_auth_errors(hass) -> None:
    """Test auth errors trigger Home Assistant reauth handling."""
    client = AsyncMock()
    client.metering_point = "571313174200318497"
    client.async_get_latest_consumption.side_effect = EloverblikAuthError("bad token")
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed: bad token"):
        await coordinator._async_update_data()


async def test_coordinator_maps_update_failures(hass) -> None:
    """Test non-auth API errors surface as update failures."""
    client = AsyncMock()
    client.metering_point = "571313174200318497"
    client.async_get_latest_consumption.side_effect = EloverblikConnectionError(
        "network down"
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with pytest.raises(UpdateFailed, match="Error fetching data: network down"):
        await coordinator._async_update_data()


async def test_coordinator_imports_new_hourly_statistics(hass) -> None:
    """Test hourly readings are imported into Home Assistant statistics."""
    client = AsyncMock()
    client.metering_point = "571313174200318497"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": {
            "start": "2024-01-02T01:00:00+01:00",
            "end": "2024-01-02T02:00:00+01:00",
            "kwh": 0.3,
        },
        "latest_hour_kwh": 0.3,
        "window_total_kwh": 0.8,
        "hourly": [
            {
                "start": "2024-01-02T00:00:00+01:00",
                "end": "2024-01-02T01:00:00+01:00",
                "kwh": 0.5,
            },
            {
                "start": "2024-01-02T01:00:00+01:00",
                "end": "2024-01-02T02:00:00+01:00",
                "kwh": 0.3,
            },
        ],
        "daily": {"2024-01-02": 0.8},
    }
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(return_value={})
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_custom.coordinator.get_instance",
            return_value=recorder,
        ),
        patch(
            "custom_components.eloverblik_custom.coordinator.async_add_external_statistics"
        ) as mock_add_external_statistics,
    ):
        await coordinator._async_update_data()

    mock_add_external_statistics.assert_called_once()
    _, metadata, statistics = mock_add_external_statistics.call_args.args
    assert (
        metadata["statistic_id"]
        == "eloverblik_custom:571313174200318497_hourly_consumption"
    )
    assert [stat["state"] for stat in statistics] == [0.5, 0.3]
    assert [round(stat["sum"], 3) for stat in statistics] == [0.5, 0.8]


async def test_coordinator_skips_existing_hourly_statistics(hass) -> None:
    """Test already imported hourly readings are not duplicated."""
    client = AsyncMock()
    client.metering_point = "571313174200318497"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": {
            "start": "2024-01-02T02:00:00+01:00",
            "end": "2024-01-02T03:00:00+01:00",
            "kwh": 0.4,
        },
        "latest_hour_kwh": 0.4,
        "window_total_kwh": 1.2,
        "hourly": [
            {
                "start": "2024-01-02T00:00:00+01:00",
                "end": "2024-01-02T01:00:00+01:00",
                "kwh": 0.5,
            },
            {
                "start": "2024-01-02T01:00:00+01:00",
                "end": "2024-01-02T02:00:00+01:00",
                "kwh": 0.3,
            },
            {
                "start": "2024-01-02T02:00:00+01:00",
                "end": "2024-01-02T03:00:00+01:00",
                "kwh": 0.4,
            },
        ],
        "daily": {"2024-01-02": 1.2},
    }
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(
        return_value={
            "eloverblik_custom:571313174200318497_hourly_consumption": [
                {"start": 1704153600.0, "sum": 0.8}
            ]
        }
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_custom.coordinator.get_instance",
            return_value=recorder,
        ),
        patch(
            "custom_components.eloverblik_custom.coordinator.async_add_external_statistics"
        ) as mock_add_external_statistics,
    ):
        await coordinator._async_update_data()

    mock_add_external_statistics.assert_called_once()
    _, _, statistics = mock_add_external_statistics.call_args.args
    assert [stat["state"] for stat in statistics] == [0.4]
    assert [round(stat["sum"], 3) for stat in statistics] == [1.2]
