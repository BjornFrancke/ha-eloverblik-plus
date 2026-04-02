"""Tests for the Eloverblik sensor entity."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from custom_components.eloverblik_plus.sensor import (
    EloverblikDailyConsumptionSensor,
    EloverblikEnergySensor,
    EloverblikLatestHourStartSensor,
    MAX_DAILY_ATTRIBUTE_POINTS,
    MAX_HOURLY_ATTRIBUTE_POINTS,
)


def _build_coordinator(data: dict | None) -> Mock:
    """Create the minimal coordinator shape the entity needs."""
    coordinator = Mock()
    coordinator.data = data
    coordinator.client = SimpleNamespace(_local_time_zone=UTC)
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
        "999999999999999999",
    )

    assert sensor.native_value == 0.5
    assert sensor.state_class is None
    assert sensor.extra_state_attributes == {
        "metering_point": "999999999999999999",
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
    sensor = EloverblikEnergySensor(_build_coordinator(None), "999999999999999999")

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
        "999999999999999999",
    )

    assert sensor.extra_state_attributes == {
        "metering_point": "999999999999999999",
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
        "999999999999999999",
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
        "999999999999999999",
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "api_end_utc": None,
        "local_start": None,
        "local_end": None,
    }


def test_daily_consumption_sensors_expose_today_and_yesterday_totals() -> None:
    """Test the daily summary sensors surface local-day values."""
    sensor_today = EloverblikDailyConsumptionSensor(
        _build_coordinator(
            {
                "latest_hour": None,
                "latest_hour_kwh": None,
                "window_total_kwh": 0.0,
                "hourly": [],
                "daily": {
                    "2024-01-03": 1.4,
                    "2024-01-02": 2.0,
                },
            }
        ),
        "999999999999999999",
        offset_days=0,
        name="Today consumption",
        unique_suffix="today_consumption",
    )
    sensor_yesterday = EloverblikDailyConsumptionSensor(
        sensor_today.coordinator,
        "999999999999999999",
        offset_days=1,
        name="Yesterday consumption",
        unique_suffix="yesterday_consumption",
    )

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN206
            return cls(2024, 1, 3, 12, 0, tzinfo=tz)

    from custom_components.eloverblik_plus import sensor as sensor_module

    original_datetime = sensor_module.datetime
    sensor_module.datetime = FixedDateTime
    try:
        assert sensor_today.native_value == 1.4
        assert sensor_yesterday.native_value == 2.0
    finally:
        sensor_module.datetime = original_datetime


def test_sensor_limits_large_attribute_payloads() -> None:
    """Test large hourly/daily payloads are trimmed to HA-safe sizes."""
    hourly = []
    for index in range(120):
        hour_start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC).timestamp() + index * 3600
        hour_end = hour_start + 3600
        hourly.append(
            {
                "api_start_utc": datetime.fromtimestamp(hour_start, tz=UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "api_end_utc": datetime.fromtimestamp(hour_end, tz=UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "start": datetime.fromtimestamp(hour_start, tz=UTC).isoformat(),
                "end": datetime.fromtimestamp(hour_end, tz=UTC).isoformat(),
                "kwh": 0.5,
            }
        )

    daily = {f"2024-01-{day:02d}": float(day) for day in range(1, 51)}
    sensor = EloverblikEnergySensor(
        _build_coordinator(
            {
                "latest_hour": hourly[-1],
                "latest_hour_kwh": 0.5,
                "window_total_kwh": 12.3,
                "hourly": hourly,
                "daily": daily,
            }
        ),
        "999999999999999999",
    )

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert len(attributes["hourly_data"]) == MAX_HOURLY_ATTRIBUTE_POINTS
    assert attributes["hourly_data"][-1] == hourly[-1]
    assert len(attributes["daily_data"]) == MAX_DAILY_ATTRIBUTE_POINTS
    assert list(attributes["daily_data"].keys())[-1] == "2024-01-50"
