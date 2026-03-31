"""Tests for the Eloverblik Custom config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.eloverblik_custom.api import (
    EloverblikAuthError,
    EloverblikConnectionError,
)
from custom_components.eloverblik_custom.const import (
    CONF_METERING_POINT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

from .conftest import MOCK_ACCESS_TOKEN, MOCK_METERING_POINT, MOCK_REFRESH_TOKEN


async def test_user_flow_success(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test a successful user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.eloverblik_custom.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            return_value=MOCK_ACCESS_TOKEN
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
                CONF_METERING_POINT: MOCK_METERING_POINT,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Eloverblik ({MOCK_METERING_POINT})"
    assert result["data"] == {
        CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
        CONF_METERING_POINT: MOCK_METERING_POINT,
    }


async def test_user_flow_invalid_auth(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test config flow with invalid authentication."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_custom.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            side_effect=EloverblikAuthError("Invalid token")
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFRESH_TOKEN: "bad_token",
                CONF_METERING_POINT: MOCK_METERING_POINT,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test config flow with connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_custom.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            side_effect=EloverblikConnectionError("Connection failed")
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
                CONF_METERING_POINT: MOCK_METERING_POINT,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "connection"}


async def test_duplicate_entry(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test config flow aborts on duplicate metering point."""
    # First entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_custom.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            return_value=MOCK_ACCESS_TOKEN
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
                CONF_METERING_POINT: MOCK_METERING_POINT,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Second entry with same metering point should abort
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_custom.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            return_value=MOCK_ACCESS_TOKEN
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
                CONF_METERING_POINT: MOCK_METERING_POINT,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
