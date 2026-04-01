"""Tests for the Eloverblik sensor entity."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

from homeassistant.components.sensor import SensorStateClass

from custom_components.eloverblik_plus.sensor import (
    EloverblikEnergySensor,
    EloverblikLatestHourStartSensor,
)


def _build_coordinator(data: dict | None) -> Mock:
    """Create the minimal coordinator shape the entity needs."""
    coordinator = Mock()
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.async_add_listener.return_value = lambda: None
    return coordinator


def test_sensor_exposes_consumption_state_and_attributes() -> None:
    """Test the sensor state and exposed attributes."""
    sensor = EloverblikEnergySensor(
        _build_coordinator(
            {
                "latest_hour": {
                    "api_start_utc": "2024-01-01T23:00:00Z",
                    "api_end_utc": "2024-01-02T00:00:00Z",
                    "start": "2024-01-02T00:00:00+01:00",
                    "end": "2024-01-02T01:00:00+01:00",
                    "kwh": 0.5,
                },
                "latest_hour_kwh": 0.5,
                "window_total_kwh": 2.0,
                "hourly": [
                    {
                        "api_start_utc": "2024-01-01T23:00:00Z",
                        "api_end_utc": "2024-01-02T00:00:00Z",
                        "start": "2024-01-02T00:00:00+01:00",
                        "end": "2024-01-02T01:00:00+01:00",
                        "kwh": 0.5,
                    }
                ],
                "daily": {"2024-01-02": 2.0},
            }
        ),
        "571313174200318497",
    )

    assert sensor.native_value == 0.5
    assert sensor.state_class is SensorStateClass.MEASUREMENT
    assert sensor.extra_state_attributes == {
        "metering_point": "571313174200318497",
        "latest_hour_api_start_utc": "2024-01-01T23:00:00Z",
        "latest_hour_api_end_utc": "2024-01-02T00:00:00Z",
        "latest_hour_start": "2024-01-02T00:00:00+01:00",
        "latest_hour_end": "2024-01-02T01:00:00+01:00",
        "window_total_kwh": 2.0,
        "hourly_data": [
            {
                "api_start_utc": "2024-01-01T23:00:00Z",
                "api_end_utc": "2024-01-02T00:00:00Z",
                "start": "2024-01-02T00:00:00+01:00",
                "end": "2024-01-02T01:00:00+01:00",
                "kwh": 0.5,
            }
        ],
        "daily_data": {"2024-01-02": 2.0},
    }


def test_sensor_returns_none_without_data() -> None:
    """Test the sensor handles missing coordinator data."""
    sensor = EloverblikEnergySensor(_build_coordinator(None), "571313174200318497")

    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None


def test_sensor_keeps_empty_hourly_breakdown() -> None:
    """Test the sensor keeps the data shape even without hourly readings."""
    sensor = EloverblikEnergySensor(
        _build_coordinator(
            {
                "latest_hour": None,
                "latest_hour_kwh": None,
                "window_total_kwh": 0.0,
                "hourly": [],
                "daily": {},
            }
        ),
        "571313174200318497",
    )

    assert sensor.extra_state_attributes == {
        "metering_point": "571313174200318497",
        "latest_hour_api_start_utc": None,
        "latest_hour_api_end_utc": None,
        "latest_hour_start": None,
        "latest_hour_end": None,
        "window_total_kwh": 0.0,
        "hourly_data": [],
        "daily_data": {},
    }


def test_timestamp_sensor_exposes_latest_api_hour() -> None:
    """Test the built-in timestamp sensor exposes the API hour start."""
    sensor = EloverblikLatestHourStartSensor(
        _build_coordinator(
            {
                "latest_hour": {
                    "api_start_utc": "2024-01-01T23:00:00Z",
                    "api_end_utc": "2024-01-02T00:00:00Z",
                    "start": "2024-01-02T00:00:00+01:00",
                    "end": "2024-01-02T01:00:00+01:00",
                    "kwh": 0.5,
                },
                "latest_hour_kwh": 0.5,
                "window_total_kwh": 2.0,
                "hourly": [],
                "daily": {},
            }
        ),
        "571313174200318497",
    )

    assert sensor.native_value == datetime(2024, 1, 1, 23, 0, tzinfo=UTC)
    assert sensor.extra_state_attributes == {
        "api_end_utc": "2024-01-02T00:00:00Z",
        "local_start": "2024-01-02T00:00:00+01:00",
        "local_end": "2024-01-02T01:00:00+01:00",
    }


def test_timestamp_sensor_handles_missing_latest_hour() -> None:
    """Test the timestamp sensor keeps a consistent empty shape."""
    sensor = EloverblikLatestHourStartSensor(
        _build_coordinator(
            {
                "latest_hour": None,
                "latest_hour_kwh": None,
                "window_total_kwh": 0.0,
                "hourly": [],
                "daily": {},
            }
        ),
        "571313174200318497",
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "api_end_utc": None,
        "local_start": None,
        "local_end": None,
    }
