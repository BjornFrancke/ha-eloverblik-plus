"""Tests for the Eloverblik Plus config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eloverblik_plus.api import (
    EloverblikAuthError,
    EloverblikConnectionError,
)
from custom_components.eloverblik_plus.const import (
    CONF_METERING_POINT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

from .conftest import MOCK_ACCESS_TOKEN, MOCK_METERING_POINT, MOCK_REFRESH_TOKEN

SINGLE_METERING_POINT = [
    {
        CONF_METERING_POINT: MOCK_METERING_POINT,
        "label": f"{MOCK_METERING_POINT} - Testvej 1, 4400 Kalundborg",
    }
]
MULTIPLE_METERING_POINTS = [
    {
        CONF_METERING_POINT: MOCK_METERING_POINT,
        "label": f"{MOCK_METERING_POINT} - Testvej 1, 4400 Kalundborg",
    },
    {
        CONF_METERING_POINT: "571313174200000001",
        "label": "571313174200000001 - Eksempelvej 2, 2100 Koebenhavn O",
    },
]


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
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)
        mock_client.async_get_metering_points = AsyncMock(
            return_value=SINGLE_METERING_POINT
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Eloverblik Plus ({MOCK_METERING_POINT})"
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
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            side_effect=EloverblikAuthError("Invalid token")
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: "bad_token"},
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
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            side_effect=EloverblikConnectionError("Connection failed")
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "connection"}


async def test_user_flow_prompts_for_metering_point_selection(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test config flow shows a selection step when multiple meters exist."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)
        mock_client.async_get_metering_points = AsyncMock(
            return_value=MULTIPLE_METERING_POINTS
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "select_metering_point"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_METERING_POINT: MULTIPLE_METERING_POINTS[1][CONF_METERING_POINT]
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == (
        f"Eloverblik Plus ({MULTIPLE_METERING_POINTS[1][CONF_METERING_POINT]})"
    )
    assert result["data"] == {
        CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
        CONF_METERING_POINT: MULTIPLE_METERING_POINTS[1][CONF_METERING_POINT],
    }


async def test_user_flow_no_metering_points(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test config flow errors when no metering points are available."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)
        mock_client.async_get_metering_points = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "no_metering_points"}


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
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)
        mock_client.async_get_metering_points = AsyncMock(
            return_value=SINGLE_METERING_POINT
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Second entry with same metering point should abort
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)
        mock_client.async_get_metering_points = AsyncMock(
            return_value=SINGLE_METERING_POINT
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_success(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test successful reauthentication."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Eloverblik Plus ({MOCK_METERING_POINT})",
        data={
            CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
            CONF_METERING_POINT: MOCK_METERING_POINT,
        },
        unique_id=MOCK_METERING_POINT,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(
            "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
        ) as mock_client_class,
        patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=True)),
    ):
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(return_value=MOCK_ACCESS_TOKEN)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: "new_refresh_token"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_REFRESH_TOKEN] == "new_refresh_token"


async def test_reauth_flow_invalid_auth(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test reauthentication with invalid credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Eloverblik Plus ({MOCK_METERING_POINT})",
        data={
            CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
            CONF_METERING_POINT: MOCK_METERING_POINT,
        },
        unique_id=MOCK_METERING_POINT,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    with patch(
        "custom_components.eloverblik_plus.config_flow.EloverblikApiClient",
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.async_get_access_token = AsyncMock(
            side_effect=EloverblikAuthError("Invalid token")
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REFRESH_TOKEN: "bad_token"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "auth"}
