"""Frontend helpers for bundled Eloverblik Lovelace assets."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import LovelaceData
from homeassistant.components.lovelace.const import (
    CONF_RESOURCE_TYPE_WS,
    LOVELACE_DATA,
    MODE_STORAGE,
)
from homeassistant.components.lovelace.const import (
    DOMAIN as LOVELACE_DOMAIN,
)
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER

FRONTEND_DIRECTORY = Path(__file__).parent / "frontend"
FRONTEND_URL_BASE = f"/{DOMAIN}"
FRONTEND_DATA_KEY = f"{DOMAIN}_frontend"
CARD_FILENAME = "eloverblik-hourly-card.js"
CARD_RESOURCE_URL = f"{FRONTEND_URL_BASE}/{CARD_FILENAME}"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register static assets and auto-add the bundled Lovelace card."""
    frontend_state = hass.data.setdefault(
        FRONTEND_DATA_KEY,
        {
            "static_registered": False,
            "resource_registered": False,
        },
    )

    if not frontend_state["static_registered"]:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    FRONTEND_URL_BASE,
                    str(FRONTEND_DIRECTORY),
                    cache_headers=False,
                )
            ]
        )
        frontend_state["static_registered"] = True

    if frontend_state["resource_registered"]:
        return

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        LOGGER.debug(
            "Skipping Lovelace resource registration; Lovelace data unavailable"
        )
        return

    if lovelace_data.resource_mode != MODE_STORAGE:
        LOGGER.info(
            "Skipping automatic Lovelace card registration because resources are"
            " not in storage mode. Add %s manually if needed.",
            CARD_RESOURCE_URL,
        )
        frontend_state["resource_registered"] = True
        return

    await _async_register_lovelace_resource(lovelace_data)
    frontend_state["resource_registered"] = True


async def _async_register_lovelace_resource(lovelace_data: LovelaceData) -> None:
    """Register the bundled card as a Lovelace module resource once."""
    resources = lovelace_data.resources
    await resources.async_get_info()

    if any(
        resource.get(CONF_URL) == CARD_RESOURCE_URL
        for resource in resources.async_items()
    ):
        return

    await resources.async_create_item(
        {
            CONF_RESOURCE_TYPE_WS: "module",
            CONF_URL: CARD_RESOURCE_URL,
        }
    )
    LOGGER.info(
        "Registered bundled Eloverblik Lovelace card at %s via %s storage.",
        CARD_RESOURCE_URL,
        LOVELACE_DOMAIN,
    )
