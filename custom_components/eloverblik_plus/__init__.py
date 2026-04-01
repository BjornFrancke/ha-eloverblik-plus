"""The Eloverblik Plus integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
import voluptuous as vol

from pyeloverblik import LOCAL_TIME_ZONE, EloverblikApiClient

from .const import (
    CONF_METERING_POINT,
    CONF_REFRESH_TOKEN,
    DEFAULT_HISTORY_DAYS,
    DOMAIN,
    MAX_TIME_SERIES_DAYS,
    SERVICE_BACKFILL_HISTORY,
    SERVICE_FIELD_DAYS,
)
from .coordinator import EloverblikDataUpdateCoordinator
from .frontend import async_setup_frontend

PLATFORMS: list[Platform] = [Platform.SENSOR]
SERVICE_BACKFILL_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_METERING_POINT): str,
        vol.Optional(SERVICE_FIELD_DAYS, default=DEFAULT_HISTORY_DAYS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_TIME_SERIES_DAYS)
        ),
    }
)


@dataclass
class EloverblikData:
    """Runtime data for the Eloverblik integration."""

    client: EloverblikApiClient
    coordinator: EloverblikDataUpdateCoordinator


EloverblikConfigEntry: TypeAlias = ConfigEntry[EloverblikData]


async def _async_handle_backfill_history(
    hass: HomeAssistant, service_call: ServiceCall
) -> None:
    """Rebuild imported statistics for a selected metering point."""
    domain_data = hass.data.get(DOMAIN, {})
    entries_by_id: dict[str, EloverblikConfigEntry] = domain_data.get("entries", {})
    entries = list(entries_by_id.values())
    metering_point = service_call.data.get(CONF_METERING_POINT)

    if not entries:
        raise ServiceValidationError("No Eloverblik Plus entries are loaded.")

    if metering_point is None:
        if len(entries) != 1:
            raise ServiceValidationError(
                "Specify metering_point when multiple Eloverblik Plus entries exist."
            )
        entry = entries[0]
    else:
        entry = next(
            (
                config_entry
                for config_entry in entries
                if config_entry.data[CONF_METERING_POINT] == metering_point
            ),
            None,
        )
        if entry is None:
            raise ServiceValidationError(
                f"Could not find Eloverblik Plus metering point {metering_point}."
            )

    await entry.runtime_data.coordinator.async_backfill_history(
        service_call.data[SERVICE_FIELD_DAYS]
    )


async def async_setup_entry(hass: HomeAssistant, entry: EloverblikConfigEntry) -> bool:
    """Set up Eloverblik Plus from a config entry."""
    await async_setup_frontend(hass)

    session = async_get_clientsession(hass)
    local_time_zone = dt_util.get_time_zone(hass.config.time_zone) or LOCAL_TIME_ZONE
    client = EloverblikApiClient(
        session=session,
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        metering_point=entry.data[CONF_METERING_POINT],
        local_time_zone=local_time_zone,
    )

    coordinator = EloverblikDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = EloverblikData(client=client, coordinator=coordinator)
    domain_data = hass.data.setdefault(DOMAIN, {"entries": {}})
    domain_data["entries"][entry.entry_id] = entry

    if not hass.services.has_service(DOMAIN, SERVICE_BACKFILL_HISTORY):
        async def async_handle_backfill(service_call: ServiceCall) -> None:
            """Handle the manual history backfill service."""
            await _async_handle_backfill_history(hass, service_call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_BACKFILL_HISTORY,
            async_handle_backfill,
            schema=SERVICE_BACKFILL_HISTORY_SCHEMA,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EloverblikConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    domain_data = hass.data.get(DOMAIN)
    if domain_data is None:
        return True

    entries_by_id: dict[str, EloverblikConfigEntry] = domain_data.get("entries", {})
    entries_by_id.pop(entry.entry_id, None)

    if (
        not entries_by_id
        and hass.services.has_service(DOMAIN, SERVICE_BACKFILL_HISTORY)
    ):
        hass.services.async_remove(DOMAIN, SERVICE_BACKFILL_HISTORY)
        hass.data.pop(DOMAIN, None)

    return True
