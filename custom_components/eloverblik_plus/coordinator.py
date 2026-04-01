"""DataUpdateCoordinator for Eloverblik."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.unit_conversion import EnergyConverter

from .api import (
    LOCAL_TIME_ZONE,
    EloverblikApiClient,
    EloverblikAuthError,
    EloverblikError,
)
from .const import (
    DEFAULT_HISTORY_DAYS,
    DEFAULT_RECENT_HISTORY_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_TIME_SERIES_DAYS,
)


class EloverblikDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching Eloverblik data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EloverblikApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    def _get_statistic_id(self) -> str:
        """Return the statistic ID for hourly consumption imports."""
        return f"{DOMAIN}:{self.client.metering_point}_hourly_consumption"

    async def _async_get_last_imported_hour_start(self) -> datetime | None:
        """Return the latest imported hourly statistic start time."""
        try:
            recorder = get_instance(self.hass)
        except KeyError:
            return None

        statistic_id = self._get_statistic_id()
        last_stats = await recorder.async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            statistic_id,
            True,
            {"sum"},
        )
        if not last_stats or statistic_id not in last_stats:
            return None

        last_stat = last_stats[statistic_id][0]
        return datetime.fromtimestamp(last_stat["start"], tz=LOCAL_TIME_ZONE)

    def _get_fetch_window(
        self, last_imported_hour_start: datetime | None
    ) -> tuple[str, str]:
        """Return the date window to request from Eloverblik."""
        now = datetime.now(LOCAL_TIME_ZONE)
        recent_window_start = now - timedelta(days=DEFAULT_RECENT_HISTORY_DAYS)

        if last_imported_hour_start is None:
            start = now - timedelta(days=DEFAULT_HISTORY_DAYS)
        else:
            catch_up_start = last_imported_hour_start - timedelta(days=1)
            start = min(recent_window_start, catch_up_start)

        start = max(start, now - timedelta(days=MAX_TIME_SERIES_DAYS))
        end = now + timedelta(days=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    async def _async_import_hourly_statistics(
        self,
        data: dict[str, Any],
        *,
        last_stat_start: datetime | None = None,
    ) -> None:
        """Import hourly consumption points into Home Assistant statistics."""
        hourly = data.get("hourly", [])
        if not hourly:
            return

        try:
            recorder = get_instance(self.hass)
        except KeyError:
            return

        statistic_id = self._get_statistic_id()
        running_sum = 0.0
        if last_stat_start is not None:
            last_stats = await recorder.async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                statistic_id,
                True,
                {"sum"},
            )
            if last_stats and statistic_id in last_stats:
                last_stat = last_stats[statistic_id][0]
                running_sum = float(last_stat.get("sum", 0.0))

        statistics: list[StatisticData] = []
        for entry in hourly:
            start_timestamp = entry.get("api_start_utc", entry["start"])
            start_dt = datetime.fromisoformat(start_timestamp.replace("Z", "+00:00"))
            if last_stat_start is not None and start_dt <= last_stat_start:
                continue

            running_sum += entry["kwh"]
            statistics.append(
                StatisticData(start=start_dt, state=entry["kwh"], sum=running_sum)
            )

        if not statistics:
            return

        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"{self.client.metering_point} hourly consumption",
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_class=EnergyConverter.UNIT_CLASS,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )
        async_add_external_statistics(self.hass, metadata, statistics)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Eloverblik API."""
        try:
            last_stat_start = await self._async_get_last_imported_hour_start()
            start_date, end_date = self._get_fetch_window(last_stat_start)
            data = await self.client.async_get_latest_consumption(
                start_date=start_date,
                end_date=end_date,
            )
            await self._async_import_hourly_statistics(
                data,
                last_stat_start=last_stat_start,
            )
            return data
        except EloverblikAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except EloverblikError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
