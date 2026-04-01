"""Constants for the Eloverblik Plus integration."""

from logging import getLogger

LOGGER = getLogger(__package__)

DOMAIN = "eloverblik_plus"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_METERING_POINT = "metering_point"

SERVICE_BACKFILL_HISTORY = "backfill_history"
SERVICE_FIELD_DAYS = "days"

DEFAULT_SCAN_INTERVAL = 3600  # 1 hour
DEFAULT_HISTORY_DAYS = 7
DEFAULT_RECENT_HISTORY_DAYS = 3
MAX_TIME_SERIES_DAYS = 730

ATTRIBUTION = "Data provided by Eloverblik (Energinet)"
