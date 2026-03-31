"""Tests for the Eloverblik data coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

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
    client.async_get_latest_consumption.return_value = {"total_kwh": 1.23}
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    result = await coordinator._async_update_data()

    assert result == {"total_kwh": 1.23}


async def test_coordinator_maps_auth_errors(hass) -> None:
    """Test auth errors trigger Home Assistant reauth handling."""
    client = AsyncMock()
    client.async_get_latest_consumption.side_effect = EloverblikAuthError("bad token")
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed: bad token"):
        await coordinator._async_update_data()


async def test_coordinator_maps_update_failures(hass) -> None:
    """Test non-auth API errors surface as update failures."""
    client = AsyncMock()
    client.async_get_latest_consumption.side_effect = EloverblikConnectionError(
        "network down"
    )
    coordinator = EloverblikDataUpdateCoordinator(hass, client)

    with pytest.raises(UpdateFailed, match="Error fetching data: network down"):
        await coordinator._async_update_data()
