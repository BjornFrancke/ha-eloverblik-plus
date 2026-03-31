"""DataUpdateCoordinator for Eloverblik."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EloverblikApiClient, EloverblikAuthError, EloverblikError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER


class EloverblikDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching Eloverblik data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EloverblikApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Eloverblik API."""
        try:
            return await self.client.async_get_latest_consumption()
        except EloverblikAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except EloverblikError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
