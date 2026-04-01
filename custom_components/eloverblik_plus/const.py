"""Constants for the Eloverblik Plus integration."""

from logging import getLogger

LOGGER = getLogger(__package__)

DOMAIN = "eloverblik_plus"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_METERING_POINT = "metering_point"

API_BASE_URL = "https://api.eloverblik.dk/CustomerApi/api"
API_TOKEN_URL = f"{API_BASE_URL}/Token"
API_METERING_POINTS_URL = f"{API_BASE_URL}/meteringpoints/meteringpoints"
API_METER_DATA_URL = f"{API_BASE_URL}/MeterData/GetTimeSeries"

DEFAULT_SCAN_INTERVAL = 3600  # 1 hour
DEFAULT_HISTORY_DAYS = 7
DEFAULT_RECENT_HISTORY_DAYS = 3
MAX_TIME_SERIES_DAYS = 730

ACCESS_TOKEN_CACHE_TTL_SECONDS = 23 * 60 * 60
ACCESS_TOKEN_REFRESH_BUFFER_SECONDS = 15 * 60

MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1
MAX_RETRY_DELAY_SECONDS = 60
RETRYABLE_HTTP_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

ATTRIBUTION = "Data provided by Eloverblik (Energinet)"
