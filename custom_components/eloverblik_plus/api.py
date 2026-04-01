"""Async API client for Eloverblik."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, tzinfo
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    ACCESS_TOKEN_CACHE_TTL_SECONDS,
    ACCESS_TOKEN_REFRESH_BUFFER_SECONDS,
    API_METER_DATA_URL,
    API_METERING_POINTS_URL,
    API_TOKEN_URL,
    DEFAULT_HISTORY_DAYS,
    LOGGER,
    MAX_RETRY_ATTEMPTS,
    MAX_RETRY_DELAY_SECONDS,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRYABLE_HTTP_STATUS_CODES,
)

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
        local_time_zone: tzinfo = LOCAL_TIME_ZONE,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._refresh_token = refresh_token
        self._metering_point = metering_point
        self._local_time_zone = local_time_zone
        self._access_token: str | None = None
        self._access_token_expires_at: datetime | None = None

    @property
    def metering_point(self) -> str:
        """Return the configured metering point ID."""
        return self._metering_point

    @staticmethod
    def _format_metering_point_label(metering_point: dict[str, Any]) -> str:
        """Build a readable label for a metering point choice."""
        metering_point_id = metering_point["meteringPointId"]
        address_parts = [
            " ".join(
                part
                for part in (
                    metering_point.get("streetName"),
                    metering_point.get("buildingNumber"),
                )
                if part
            ).strip(),
            " ".join(
                part
                for part in (
                    metering_point.get("postcode"),
                    metering_point.get("cityName"),
                )
                if part
            ).strip(),
        ]
        address = ", ".join(part for part in address_parts if part)
        return f"{metering_point_id} - {address}" if address else str(metering_point_id)

    def _invalidate_access_token(self) -> None:
        """Clear any cached access token."""
        self._access_token = None
        self._access_token_expires_at = None

    def _has_valid_cached_access_token(self) -> bool:
        """Return whether a cached access token can still be reused."""
        if self._access_token is None or self._access_token_expires_at is None:
            return False

        refresh_at = self._access_token_expires_at - timedelta(
            seconds=ACCESS_TOKEN_REFRESH_BUFFER_SECONDS
        )
        return datetime.now(UTC) < refresh_at

    @staticmethod
    def _get_retry_delay(retry_after: str | None, attempt: int) -> float:
        """Return the delay to use before the next retry."""
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), MAX_RETRY_DELAY_SECONDS))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                return max(
                    0.0,
                    min(
                        (retry_at - datetime.now(UTC)).total_seconds(),
                        MAX_RETRY_DELAY_SECONDS,
                    ),
                )

        backoff_seconds = RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
        return float(min(backoff_seconds, MAX_RETRY_DELAY_SECONDS))

    async def _async_request_json(
        self,
        method: str,
        url: str,
        *,
        auth_error_message: str,
        **request_kwargs: Any,
    ) -> dict[str, Any]:
        """Perform an API request with bounded retries for transient failures."""
        request = getattr(self._session, method)

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                async with request(url, **request_kwargs) as response:
                    if response.status == 401:
                        raise EloverblikAuthError(auth_error_message)

                    if (
                        response.status in RETRYABLE_HTTP_STATUS_CODES
                        and attempt < MAX_RETRY_ATTEMPTS
                    ):
                        retry_delay = self._get_retry_delay(
                            response.headers.get("Retry-After"), attempt
                        )
                        LOGGER.warning(
                            (
                                "Eloverblik API returned %s for %s, "
                                "retrying in %.1f seconds"
                            ),
                            response.status,
                            url,
                            retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                        continue

                    response.raise_for_status()
                    return await response.json()
            except EloverblikAuthError:
                raise
            except aiohttp.ClientResponseError as err:
                if (
                    err.status in RETRYABLE_HTTP_STATUS_CODES
                    and attempt < MAX_RETRY_ATTEMPTS
                ):
                    retry_delay = self._get_retry_delay(
                        err.headers.get("Retry-After") if err.headers else None,
                        attempt,
                    )
                    LOGGER.warning(
                        (
                            "Eloverblik API request to %s failed with %s, "
                            "retrying in %.1f seconds"
                        ),
                        url,
                        err.status,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                raise EloverblikConnectionError(
                    f"Eloverblik API request failed: {err}"
                ) from err
            except (
                TimeoutError,
                aiohttp.ClientConnectionError,
                aiohttp.ServerTimeoutError,
            ) as err:
                if attempt < MAX_RETRY_ATTEMPTS:
                    retry_delay = self._get_retry_delay(None, attempt)
                    LOGGER.warning(
                        (
                            "Transient Eloverblik API error for %s: %s; "
                            "retrying in %.1f seconds"
                        ),
                        url,
                        err,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                raise EloverblikConnectionError(
                    f"Error connecting to Eloverblik API: {err}"
                ) from err
            except aiohttp.ClientError as err:
                raise EloverblikConnectionError(
                    f"Error connecting to Eloverblik API: {err}"
                ) from err

        raise EloverblikConnectionError(f"Error connecting to Eloverblik API: {url}")

    async def async_get_access_token(self, *, force_refresh: bool = False) -> str:
        """Exchange refresh token for an access token."""
        if not force_refresh and self._has_valid_cached_access_token():
            return self._access_token  # type: ignore[return-value]

        headers = {"Authorization": f"Bearer {self._refresh_token}"}
        data = await self._async_request_json(
            "get",
            API_TOKEN_URL,
            headers=headers,
            auth_error_message="Invalid refresh token",
        )

        self._access_token = data["result"]
        self._access_token_expires_at = datetime.now(UTC) + timedelta(
            seconds=ACCESS_TOKEN_CACHE_TTL_SECONDS
        )
        return self._access_token

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

        return await self._async_request_json(
            "post",
            url,
            headers=headers,
            json=body,
            auth_error_message="Access token expired or invalid",
        )

    async def async_get_metering_points(
        self, access_token: str
    ) -> list[dict[str, str]]:
        """Fetch metering points available for the authenticated customer."""
        data = await self._async_request_json(
            "get",
            API_METERING_POINTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            auth_error_message="Access token expired or invalid",
        )

        metering_points: list[dict[str, str]] = []
        for metering_point in data.get("result", []):
            metering_point_id = metering_point.get("meteringPointId")
            if not metering_point_id:
                continue

            metering_points.append(
                {
                    "metering_point": str(metering_point_id),
                    "label": self._format_metering_point_label(metering_point),
                }
            )

        return metering_points

    async def async_get_latest_consumption(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the latest consumption data.

        Returns the latest hourly reading plus hourly and daily breakdowns.
        """
        access_token = await self.async_get_access_token()
        try:
            data = await self.async_get_time_series(
                access_token,
                start_date=start_date,
                end_date=end_date,
            )
        except EloverblikAuthError:
            self._invalidate_access_token()
            access_token = await self.async_get_access_token(force_refresh=True)
            data = await self.async_get_time_series(
                access_token,
                start_date=start_date,
                end_date=end_date,
            )
        return self._parse_time_series(data, local_time_zone=self._local_time_zone)

    @staticmethod
    def _parse_time_series(
        data: dict[str, Any],
        *,
        local_time_zone: tzinfo = LOCAL_TIME_ZONE,
    ) -> dict[str, Any]:
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
            local_start = start_time.astimezone(local_time_zone)

            for point in period.get("Point", []):
                offset = int(point["position"]) - 1
                point_start = start_time + timedelta(hours=offset)
                point_end = point_start + timedelta(hours=1)
                api_start = point_start.astimezone(UTC)
                api_end = point_end.astimezone(UTC)
                time_slot = point_start.astimezone(local_time_zone)
                end_slot = point_end.astimezone(local_time_zone)
                quantity = float(point["out_Quantity.quantity"])
                day_total += quantity
                hourly.append(
                    {
                        "api_start_utc": api_start.isoformat().replace("+00:00", "Z"),
                        "api_end_utc": api_end.isoformat().replace("+00:00", "Z"),
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
