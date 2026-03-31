"""Tests for the Eloverblik sensor entity."""

from __future__ import annotations

from unittest.mock import Mock

from homeassistant.components.sensor import SensorStateClass

from custom_components.eloverblik_custom.sensor import EloverblikEnergySensor


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
                "total_kwh": 2.0,
                "hourly": [{"timestamp": "2024-01-02T00:00:00+01:00", "kwh": 0.5}],
                "daily": {"2024-01-02": 2.0},
            }
        ),
        "571313174200318497",
    )

    assert sensor.native_value == 2.0
    assert sensor.state_class is SensorStateClass.TOTAL_INCREASING
    assert sensor.extra_state_attributes == {
        "metering_point": "571313174200318497",
        "hourly_data": [{"timestamp": "2024-01-02T00:00:00+01:00", "kwh": 0.5}],
        "daily_data": {"2024-01-02": 2.0},
    }


def test_sensor_returns_none_without_data() -> None:
    """Test the sensor handles missing coordinator data."""
    sensor = EloverblikEnergySensor(_build_coordinator(None), "571313174200318497")

    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None


def test_sensor_hides_empty_hourly_breakdown() -> None:
    """Test the sensor omits attributes when there is no hourly data."""
    sensor = EloverblikEnergySensor(
        _build_coordinator({"total_kwh": 0.0, "hourly": [], "daily": {}}),
        "571313174200318497",
    )

    assert sensor.extra_state_attributes is None
