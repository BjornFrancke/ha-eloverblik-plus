"""Sensor platform for Eloverblik Plus."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EloverblikConfigEntry
from .const import ATTRIBUTION, CONF_METERING_POINT, DOMAIN
from .coordinator import EloverblikDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EloverblikConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eloverblik sensors based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    metering_point = entry.data[CONF_METERING_POINT]

    async_add_entities(
        [
            EloverblikEnergySensor(coordinator, metering_point),
            EloverblikLatestHourStartSensor(coordinator, metering_point),
        ],
    )


class EloverblikBaseSensor(
    CoordinatorEntity[EloverblikDataUpdateCoordinator], SensorEntity
):
    """Shared base entity for Eloverblik sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: EloverblikDataUpdateCoordinator,
        metering_point: str,
    ) -> None:
        """Initialize common sensor metadata."""
        super().__init__(coordinator)
        self._metering_point = metering_point
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, metering_point)},
            name=f"Eloverblik Plus {metering_point}",
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Energinet",
        )


class EloverblikEnergySensor(EloverblikBaseSensor):
    """Sensor for the latest hourly Eloverblik electricity consumption."""

    _attr_name = "Latest hourly consumption"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(
        self,
        coordinator: EloverblikDataUpdateCoordinator,
        metering_point: str,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator, metering_point)
        self._attr_unique_id = f"{metering_point}_energy"

    @property
    def native_value(self) -> float | None:
        """Return the latest hourly consumption in kWh."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("latest_hour_kwh")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the fetched hourly and daily consumption breakdown."""
        if self.coordinator.data is None:
            return None

        latest_hour = self.coordinator.data.get("latest_hour")
        hourly = self.coordinator.data.get("hourly", [])
        daily = self.coordinator.data.get("daily", {})
        return {
            "metering_point": self._metering_point,
            "latest_hour_api_start_utc": (
                latest_hour.get("api_start_utc") if latest_hour else None
            ),
            "latest_hour_api_end_utc": (
                latest_hour.get("api_end_utc") if latest_hour else None
            ),
            "latest_hour_start": latest_hour.get("start") if latest_hour else None,
            "latest_hour_end": latest_hour.get("end") if latest_hour else None,
            "window_total_kwh": self.coordinator.data.get("window_total_kwh"),
            "hourly_data": hourly,
            "daily_data": daily,
        }


class EloverblikLatestHourStartSensor(EloverblikBaseSensor):
    """Timestamp sensor for the latest hourly API interval start."""

    _attr_name = "Latest hourly interval start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: EloverblikDataUpdateCoordinator,
        metering_point: str,
    ) -> None:
        """Initialize the timestamp sensor."""
        super().__init__(coordinator, metering_point)
        self._attr_unique_id = f"{metering_point}_latest_hour_start"

    @property
    def native_value(self) -> datetime | None:
        """Return the latest hourly API start as a timezone-aware datetime."""
        if self.coordinator.data is None:
            return None

        latest_hour = self.coordinator.data.get("latest_hour")
        if latest_hour is None:
            return None

        api_start_utc = latest_hour.get("api_start_utc")
        if api_start_utc is None:
            return None

        return datetime.fromisoformat(api_start_utc.replace("Z", "+00:00"))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return matching API and local interval metadata."""
        if self.coordinator.data is None:
            return None

        latest_hour = self.coordinator.data.get("latest_hour")
        if latest_hour is None:
            return {
                "api_end_utc": None,
                "local_start": None,
                "local_end": None,
            }

        return {
            "api_end_utc": latest_hour.get("api_end_utc"),
            "local_start": latest_hour.get("start"),
            "local_end": latest_hour.get("end"),
        }
