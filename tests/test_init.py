"""Tests for the Eloverblik Custom integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eloverblik_custom.const import DOMAIN

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
    with patch(
        "custom_components.eloverblik_custom.EloverblikApiClient",
        return_value=mock_eloverblik_api,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_eloverblik_api: AsyncMock,
    enable_custom_integrations: None,
) -> None:
    """Test unloading a config entry."""
    with patch(
        "custom_components.eloverblik_custom.EloverblikApiClient",
        return_value=mock_eloverblik_api,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
