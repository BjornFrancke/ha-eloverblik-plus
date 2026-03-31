"""Config flow for Eloverblik Custom integration."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import EloverblikApiClient, EloverblikAuthError, EloverblikConnectionError
from .const import CONF_METERING_POINT, CONF_REFRESH_TOKEN, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REFRESH_TOKEN): str,
        vol.Required(CONF_METERING_POINT): str,
    }
)


class EloverblikConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eloverblik Custom."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate credentials by attempting a token exchange
            session = async_get_clientsession(self.hass)
            client = EloverblikApiClient(
                session=session,
                refresh_token=user_input[CONF_REFRESH_TOKEN],
                metering_point=user_input[CONF_METERING_POINT],
            )

            try:
                await client.async_get_access_token()
            except EloverblikAuthError:
                errors["base"] = "auth"
            except (EloverblikConnectionError, aiohttp.ClientError):
                errors["base"] = "connection"
            except Exception:
                LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                # Prevent duplicate entries for the same metering point
                await self.async_set_unique_id(user_input[CONF_METERING_POINT])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Eloverblik ({user_input[CONF_METERING_POINT]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
