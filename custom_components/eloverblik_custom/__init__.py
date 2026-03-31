"""The Eloverblik Custom integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EloverblikApiClient
from .const import CONF_METERING_POINT, CONF_REFRESH_TOKEN
from .coordinator import EloverblikDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type EloverblikConfigEntry = ConfigEntry[EloverblikData]


@dataclass
class EloverblikData:
    """Runtime data for the Eloverblik integration."""

    client: EloverblikApiClient
    coordinator: EloverblikDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: EloverblikConfigEntry
) -> bool:
    """Set up Eloverblik Custom from a config entry."""
    session = async_get_clientsession(hass)
    client = EloverblikApiClient(
        session=session,
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        metering_point=entry.data[CONF_METERING_POINT],
    )

    coordinator = EloverblikDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = EloverblikData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EloverblikConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
