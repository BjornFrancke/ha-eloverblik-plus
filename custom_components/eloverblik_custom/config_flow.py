"""Config flow for Eloverblik Custom integration."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
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

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REFRESH_TOKEN): str,
    }
)


async def _async_validate_token(
    flow: EloverblikConfigFlow,
    refresh_token: str,
    metering_point: str,
) -> dict[str, str]:
    """Validate a refresh token against the Eloverblik API."""
    session = async_get_clientsession(flow.hass)
    client = EloverblikApiClient(
        session=session,
        refresh_token=refresh_token,
        metering_point=metering_point,
    )

    try:
        await client.async_get_access_token()
    except EloverblikAuthError:
        return {"base": "auth"}
    except (EloverblikConnectionError, aiohttp.ClientError):
        return {"base": "connection"}
    except Exception:
        LOGGER.exception("Unexpected error during config flow")
        return {"base": "unknown"}

    return {}


class EloverblikConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eloverblik Custom."""

    VERSION = 1
    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await _async_validate_token(
                self,
                user_input[CONF_REFRESH_TOKEN],
                user_input[CONF_METERING_POINT],
            )
            if not errors:
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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication flow start."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication with a new refresh token."""
        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await _async_validate_token(
                self,
                user_input[CONF_REFRESH_TOKEN],
                self._reauth_entry.data[CONF_METERING_POINT],
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN]},
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={
                CONF_METERING_POINT: self._reauth_entry.data[CONF_METERING_POINT]
            },
            errors=errors,
        )
