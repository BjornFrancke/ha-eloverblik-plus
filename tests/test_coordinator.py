"""Tests for the Eloverblik data coordinator."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.eloverblik_plus.coordinator import (
    EloverblikDataUpdateCoordinator,
)
from pyeloverblik import (
    LOCAL_TIME_ZONE,
    EloverblikAuthError,
    EloverblikConnectionError,
)


class FixedDateTime(datetime):
    """Freeze coordinator time-dependent calculations for tests."""

    @classmethod
    def now(cls, tz=None):  # noqa: ANN206
        """Return a fixed point in time."""
        return cls(2026, 3, 31, 12, 0, tzinfo=tz)


async def test_coordinator_returns_latest_consumption(hass) -> None:
    """Test successful coordinator refresh."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": {
            "api_start_utc": "2024-01-01T23:00:00Z",
            "api_end_utc": "2024-01-02T00:00:00Z",
            "start": "2024-01-02T00:00:00+01:00",
            "end": "2024-01-02T01:00:00+01:00",
            "kwh": 1.23,
        },
        "latest_hour_kwh": 1.23,
        "window_total_kwh": 1.23,
        "hourly": [
            {
                "api_start_utc": "2024-01-01T23:00:00Z",
                "api_end_utc": "2024-01-02T00:00:00Z",
                "start": "2024-01-02T00:00:00+01:00",
                "end": "2024-01-02T01:00:00+01:00",
                "kwh": 1.23,
            }
        ],
        "daily": {"2024-01-02": 1.23},
    }
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            side_effect=KeyError,
        ),
    ):
        result = await coordinator._async_update_data()

    assert result["latest_hour_kwh"] == 1.23
    client.async_get_latest_consumption.assert_called_once_with(
        start_date="2026-03-24",
        end_date="2026-04-01",
    )


async def test_coordinator_maps_auth_errors(hass) -> None:
    """Test auth errors trigger Home Assistant reauth handling."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.side_effect = EloverblikAuthError("bad token")
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            side_effect=KeyError,
        ),
        pytest.raises(ConfigEntryAuthFailed, match="Authentication failed: bad token"),
    ):
        await coordinator._async_update_data()


async def test_coordinator_maps_update_failures(hass) -> None:
    """Test non-auth API errors surface as update failures."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.side_effect = EloverblikConnectionError(
        "network down"
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            side_effect=KeyError,
        ),
        pytest.raises(UpdateFailed, match="Error fetching data: network down"),
    ):
        await coordinator._async_update_data()


async def test_coordinator_imports_new_hourly_statistics(hass) -> None:
    """Test hourly readings are imported into Home Assistant statistics."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": {
            "api_start_utc": "2024-01-02T00:00:00Z",
            "api_end_utc": "2024-01-02T01:00:00Z",
            "start": "2024-01-02T01:00:00+01:00",
            "end": "2024-01-02T02:00:00+01:00",
            "kwh": 0.3,
        },
        "latest_hour_kwh": 0.3,
        "window_total_kwh": 0.8,
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
        ],
        "daily": {"2024-01-02": 0.8},
    }
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(return_value={})
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            return_value=recorder,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.async_add_external_statistics"
        ) as mock_add_external_statistics,
    ):
        await coordinator._async_update_data()

    mock_add_external_statistics.assert_called_once()
    _, metadata, statistics = mock_add_external_statistics.call_args.args
    assert (
        metadata["statistic_id"]
        == "eloverblik_plus:999999999999999999_hourly_consumption"
    )
    assert [stat["start"] for stat in statistics] == [
        datetime(2024, 1, 1, 23, 0, tzinfo=UTC),
        datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
    ]
    assert [stat["state"] for stat in statistics] == [0.5, 0.3]
    assert [round(stat["sum"], 3) for stat in statistics] == [0.5, 0.8]


async def test_coordinator_skips_existing_hourly_statistics(hass) -> None:
    """Test already imported hourly readings are not duplicated."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": {
            "api_start_utc": "2024-01-02T01:00:00Z",
            "api_end_utc": "2024-01-02T02:00:00Z",
            "start": "2024-01-02T02:00:00+01:00",
            "end": "2024-01-02T03:00:00+01:00",
            "kwh": 0.4,
        },
        "latest_hour_kwh": 0.4,
        "window_total_kwh": 1.2,
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
                "kwh": 0.4,
            },
        ],
        "daily": {"2024-01-02": 1.2},
    }
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(
        return_value={
            "eloverblik_plus:999999999999999999_hourly_consumption": [
                {"start": 1704153600.0, "sum": 0.8}
            ]
        }
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            return_value=recorder,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.async_add_external_statistics"
        ) as mock_add_external_statistics,
    ):
        await coordinator._async_update_data()

    mock_add_external_statistics.assert_called_once()
    _, _, statistics = mock_add_external_statistics.call_args.args
    assert [stat["start"] for stat in statistics] == [
        datetime(2024, 1, 2, 1, 0, tzinfo=UTC)
    ]
    assert [stat["state"] for stat in statistics] == [0.4]
    assert [round(stat["sum"], 3) for stat in statistics] == [1.2]


async def test_coordinator_uses_recent_window_for_routine_updates(hass) -> None:
    """Test routine polling uses a smaller rolling fetch window."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": None,
        "latest_hour_kwh": None,
        "window_total_kwh": 0.0,
        "hourly": [],
        "daily": {},
    }
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(
        return_value={
            "eloverblik_plus:999999999999999999_hourly_consumption": [
                {
                    "start": datetime(
                        2026, 3, 29, 0, 0, tzinfo=LOCAL_TIME_ZONE
                    ).timestamp(),
                    "sum": 12.3,
                }
            ]
        }
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            return_value=recorder,
        ),
    ):
        await coordinator._async_update_data()

    client.async_get_latest_consumption.assert_called_once_with(
        start_date="2026-03-28",
        end_date="2026-04-01",
    )


async def test_coordinator_extends_window_to_catch_up_after_downtime(hass) -> None:
    """Test polling expands the fetch window when imported statistics are stale."""
    client = AsyncMock()
    client.metering_point = "999999999999999999"
    client.async_get_latest_consumption.return_value = {
        "latest_hour": None,
        "latest_hour_kwh": None,
        "window_total_kwh": 0.0,
        "hourly": [],
        "daily": {},
    }
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(
        return_value={
            "eloverblik_plus:999999999999999999_hourly_consumption": [
                {
                    "start": datetime(
                        2026, 3, 20, 0, 0, tzinfo=LOCAL_TIME_ZONE
                    ).timestamp(),
                    "sum": 12.3,
                }
            ]
        }
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with (
        patch(
            "custom_components.eloverblik_plus.coordinator.datetime",
            FixedDateTime,
        ),
        patch(
            "custom_components.eloverblik_plus.coordinator.get_instance",
            return_value=recorder,
        ),
    ):
        await coordinator._async_update_data()

    client.async_get_latest_consumption.assert_called_once_with(
        start_date="2026-03-19",
        end_date="2026-04-01",
    )
