"""Tests for Eloverblik diagnostics support."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eloverblik_plus import EloverblikData
from custom_components.eloverblik_plus.const import (
    CONF_METERING_POINT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from custom_components.eloverblik_plus.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_refresh_token(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test diagnostics redact secrets and include runtime data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eloverblik Test",
        data={
            CONF_REFRESH_TOKEN: "secret_refresh_token",
            CONF_METERING_POINT: "999999999999999999",
        },
        unique_id="999999999999999999",
    )
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = {"latest_hour_kwh": 0.6}
    client = SimpleNamespace(
        metering_point="999999999999999999",
        _local_time_zone="Europe/Copenhagen",
        _access_token="cached_access_token",
        _access_token_expires_at=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
    )
    entry.runtime_data = EloverblikData(client=client, coordinator=coordinator)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["data"][CONF_REFRESH_TOKEN] != "secret_refresh_token"
    assert result["entry"]["data"][CONF_METERING_POINT] == "999999999999999999"
    assert result["client"] == {
        "metering_point": "999999999999999999",
        "local_time_zone": "Europe/Copenhagen",
        "has_cached_access_token": True,
        "access_token_expires_at": "2026-04-01T12:00:00+00:00",
    }
    assert result["coordinator"] == {
        "last_update_success": True,
        "data": {"latest_hour_kwh": 0.6},
    }
