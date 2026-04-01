"""Config flow for Eloverblik Plus integration."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .api import EloverblikApiClient, EloverblikAuthError, EloverblikConnectionError
from .const import CONF_METERING_POINT, CONF_REFRESH_TOKEN, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REFRESH_TOKEN): str,
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


async def _async_get_metering_points(
    flow: EloverblikConfigFlow,
    refresh_token: str,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Validate a refresh token and fetch available metering points."""
    session = async_get_clientsession(flow.hass)
    client = EloverblikApiClient(
        session=session,
        refresh_token=refresh_token,
        metering_point="",
    )

    try:
        access_token = await client.async_get_access_token()
        metering_points = await client.async_get_metering_points(access_token)
    except EloverblikAuthError:
        return {"base": "auth"}, []
    except (EloverblikConnectionError, aiohttp.ClientError):
        return {"base": "connection"}, []
    except Exception:
        LOGGER.exception("Unexpected error during config flow")
        return {"base": "unknown"}, []

    if not metering_points:
        return {"base": "no_metering_points"}, []

    return {}, metering_points


def _build_metering_point_selector(
    metering_points: list[dict[str, str]],
) -> vol.Schema:
    """Build the selector shown when multiple metering points are available."""
    return vol.Schema(
        {
            vol.Required(CONF_METERING_POINT): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(
                            value=metering_point["metering_point"],
                            label=metering_point["label"],
                        )
                        for metering_point in metering_points
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


class EloverblikConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eloverblik Plus."""

    VERSION = 1
    _reauth_entry: ConfigEntry | None = None
    _refresh_token: str | None = None
    _metering_points: list[dict[str, str]]

    async def _async_create_metering_point_entry(
        self, refresh_token: str, metering_point: str
    ) -> ConfigFlowResult:
        """Create a config entry for the selected metering point."""
        await self.async_set_unique_id(metering_point)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Eloverblik Plus ({metering_point})",
            data={
                CONF_REFRESH_TOKEN: refresh_token,
                CONF_METERING_POINT: metering_point,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            refresh_token = user_input[CONF_REFRESH_TOKEN]
            errors, metering_points = await _async_get_metering_points(
                self, refresh_token
            )
            if not errors:
                if len(metering_points) == 1:
                    return await self._async_create_metering_point_entry(
                        refresh_token,
                        metering_points[0][CONF_METERING_POINT],
                    )

                self._refresh_token = refresh_token
                self._metering_points = metering_points
                return await self.async_step_select_metering_point()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_metering_point(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle metering point selection when multiple are available."""
        if self._refresh_token is None or not getattr(self, "_metering_points", None):
            return self.async_abort(reason="unknown")

        if user_input is not None:
            return await self._async_create_metering_point_entry(
                self._refresh_token, user_input[CONF_METERING_POINT]
            )

        return self.async_show_form(
            step_id="select_metering_point",
            data_schema=_build_metering_point_selector(self._metering_points),
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
