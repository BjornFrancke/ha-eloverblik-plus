"""Tests for the Eloverblik Plus integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eloverblik_plus.const import DOMAIN

from .conftest import MOCK_METERING_POINT, MOCK_REFRESH_TOKEN


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eloverblik Test",
        data={
            "refresh_token": MOCK_REFRESH_TOKEN,
            "metering_point": MOCK_METERING_POINT,
        },
        unique_id=MOCK_METERING_POINT,
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_eloverblik_api: AsyncMock,
    enable_custom_integrations: None,
) -> None:
    """Test successful setup of a config entry."""
    with (
        patch(
            "custom_components.eloverblik_plus.EloverblikApiClient",
            return_value=mock_eloverblik_api,
        ),
        patch(
            "custom_components.eloverblik_plus.async_setup_frontend",
            new=AsyncMock(),
        ) as mock_setup_frontend,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_setup_frontend.assert_awaited_once_with(hass)
    assert (
        hass.states.get(
            "sensor.eloverblik_plus_999999999999999999_latest_hourly_consumption"
        )
        is not None
    )
    assert (
        hass.states.get(
            "sensor.eloverblik_plus_999999999999999999_latest_hourly_interval_start"
        )
        is not None
    )


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_eloverblik_api: AsyncMock,
    enable_custom_integrations: None,
) -> None:
    """Test unloading a config entry."""
    with (
        patch(
            "custom_components.eloverblik_plus.EloverblikApiClient",
            return_value=mock_eloverblik_api,
        ),
        patch(
            "custom_components.eloverblik_plus.async_setup_frontend",
            new=AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
