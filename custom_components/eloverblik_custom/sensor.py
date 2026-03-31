"""Sensor platform for Eloverblik Custom."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up Eloverblik sensor based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    metering_point = entry.data[CONF_METERING_POINT]

    async_add_entities(
        [EloverblikEnergySensor(coordinator, metering_point)],
    )


class EloverblikEnergySensor(
    CoordinatorEntity[EloverblikDataUpdateCoordinator], SensorEntity
):
    """Sensor for the latest hourly Eloverblik electricity consumption."""

    _attr_has_entity_name = True
    _attr_name = "Latest hourly consumption"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: EloverblikDataUpdateCoordinator,
        metering_point: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._metering_point = metering_point
        self._attr_unique_id = f"{metering_point}_energy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, metering_point)},
            name=f"Eloverblik {metering_point}",
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Energinet",
        )

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
            "latest_hour_start": latest_hour["start"] if latest_hour else None,
            "latest_hour_end": latest_hour["end"] if latest_hour else None,
            "window_total_kwh": self.coordinator.data.get("window_total_kwh"),
            "hourly_data": hourly,
            "daily_data": daily,
        }
