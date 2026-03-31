"""Async API client for Eloverblik."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import API_METER_DATA_URL, API_TOKEN_URL, LOGGER


class EloverblikError(Exception):
    """Base exception for Eloverblik API errors."""


class EloverblikAuthError(EloverblikError):
    """Authentication error."""


class EloverblikConnectionError(EloverblikError):
    """Connection error."""


class EloverblikApiClient:
    """Async client for the Eloverblik API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        refresh_token: str,
        metering_point: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._refresh_token = refresh_token
        self._metering_point = metering_point

    async def async_get_access_token(self) -> str:
        """Exchange refresh token for an access token."""
        headers = {"Authorization": f"Bearer {self._refresh_token}"}
        try:
            async with self._session.get(
                API_TOKEN_URL, headers=headers
            ) as response:
                if response.status == 401:
                    raise EloverblikAuthError("Invalid refresh token")
                response.raise_for_status()
                data = await response.json()
                return data["result"]
        except aiohttp.ClientError as err:
            raise EloverblikConnectionError(
                f"Error connecting to Eloverblik API: {err}"
            ) from err

    async def async_get_time_series(
        self,
        access_token: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Fetch time series data for the metering point."""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        url = f"{API_METER_DATA_URL}/{start_date}/{end_date}/Hour"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "meteringPoints": {
                "meteringPoint": [self._metering_point],
            }
        }

        try:
            async with self._session.post(
                url, headers=headers, json=body
            ) as response:
                if response.status == 401:
                    raise EloverblikAuthError("Access token expired or invalid")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise EloverblikConnectionError(
                f"Error fetching time series: {err}"
            ) from err

    async def async_get_latest_consumption(self) -> dict[str, Any]:
        """Fetch the latest consumption data.

        Returns a dict with 'total_kwh' and 'hourly' keys.
        """
        access_token = await self.async_get_access_token()
        data = await self.async_get_time_series(access_token)
        return self._parse_time_series(data)

    @staticmethod
    def _parse_time_series(data: dict[str, Any]) -> dict[str, Any]:
        """Parse the API response into consumption data."""
        result_list = data.get("result", [])
        if not result_list:
            LOGGER.warning("No results in API response")
            return {"total_kwh": 0.0, "hourly": []}

        market_doc = result_list[0].get("MyEnergyData_MarketDocument", {})
        time_series = market_doc.get("TimeSeries", [])

        if not time_series:
            LOGGER.warning("No time series found for metering point")
            return {"total_kwh": 0.0, "hourly": []}

        # Get the most recent period
        periods = time_series[0].get("Period", [])
        if not periods:
            return {"total_kwh": 0.0, "hourly": []}

        latest_period = periods[-1]
        start_time_str = latest_period["timeInterval"]["start"]
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")

        hourly: list[dict[str, Any]] = []
        total_kwh = 0.0

        for point in latest_period.get("Point", []):
            offset = int(point["position"]) - 1
            time_slot = start_time + timedelta(hours=offset)
            quantity = float(point["out_Quantity.quantity"])
            total_kwh += quantity
            hourly.append(
                {
                    "timestamp": time_slot.isoformat(),
                    "kwh": quantity,
                }
            )

        return {"total_kwh": round(total_kwh, 3), "hourly": hourly}
