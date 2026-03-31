"""Async API client for Eloverblik."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from .const import API_METER_DATA_URL, API_TOKEN_URL, DEFAULT_HISTORY_DAYS, LOGGER

LOCAL_TIME_ZONE = ZoneInfo("Europe/Copenhagen")


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

    @property
    def metering_point(self) -> str:
        """Return the configured metering point ID."""
        return self._metering_point

    async def async_get_access_token(self) -> str:
        """Exchange refresh token for an access token."""
        headers = {"Authorization": f"Bearer {self._refresh_token}"}
        try:
            async with self._session.get(API_TOKEN_URL, headers=headers) as response:
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
            start = datetime.now() - timedelta(days=DEFAULT_HISTORY_DAYS)
            start_date = start.strftime("%Y-%m-%d")
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
            async with self._session.post(url, headers=headers, json=body) as response:
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

        Returns the latest hourly reading plus hourly and daily breakdowns.
        """
        access_token = await self.async_get_access_token()
        data = await self.async_get_time_series(access_token)
        return self._parse_time_series(data)

    @staticmethod
    def _parse_time_series(data: dict[str, Any]) -> dict[str, Any]:
        """Parse the API response into consumption data.

        Iterates over all periods (days) in the response, building a
        chronological hourly list and per-day totals.
        """
        empty: dict[str, Any] = {
            "latest_hour": None,
            "latest_hour_kwh": None,
            "window_total_kwh": 0.0,
            "hourly": [],
            "daily": {},
        }

        result_list = data.get("result", [])
        if not result_list:
            LOGGER.warning("No results in API response")
            return empty

        result = result_list[0]
        success = result.get("success")
        error_code = result.get("errorCode")
        if success is False or (error_code is not None and error_code != 10000):
            error_text = result.get("errorText", "Unknown API error")
            raise EloverblikError(f"Eloverblik API error {error_code}: {error_text}")

        market_doc = result.get("MyEnergyData_MarketDocument", {})
        time_series = market_doc.get("TimeSeries", [])

        if not time_series:
            LOGGER.warning("No time series found for metering point")
            return empty

        periods = time_series[0].get("Period", [])
        if not periods:
            return empty

        hourly: list[dict[str, Any]] = []
        daily: dict[str, float] = {}
        total_kwh = 0.0

        for period in periods:
            start_time_str = period["timeInterval"]["start"]
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            day_total = 0.0
            local_start = start_time.astimezone(LOCAL_TIME_ZONE)

            for point in period.get("Point", []):
                offset = int(point["position"]) - 1
                point_start = start_time + timedelta(hours=offset)
                point_end = point_start + timedelta(hours=1)
                time_slot = point_start.astimezone(LOCAL_TIME_ZONE)
                end_slot = point_end.astimezone(LOCAL_TIME_ZONE)
                quantity = float(point["out_Quantity.quantity"])
                day_total += quantity
                hourly.append(
                    {
                        "start": time_slot.isoformat(),
                        "end": end_slot.isoformat(),
                        "kwh": quantity,
                    }
                )

            # Key by the local date of the period start
            day_key = local_start.strftime("%Y-%m-%d")
            daily[day_key] = round(day_total, 3)
            total_kwh += day_total

        latest_hour = hourly[-1] if hourly else None

        return {
            "latest_hour": latest_hour,
            "latest_hour_kwh": latest_hour["kwh"] if latest_hour else None,
            "window_total_kwh": round(total_kwh, 3),
            "hourly": hourly,
            "daily": daily,
        }
