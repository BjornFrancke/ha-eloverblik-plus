"""Constants for the Eloverblik Custom integration."""

from logging import getLogger

LOGGER = getLogger(__package__)

DOMAIN = "eloverblik_custom"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_METERING_POINT = "metering_point"

API_BASE_URL = "https://api.eloverblik.dk/CustomerApi/api"
API_TOKEN_URL = f"{API_BASE_URL}/Token"
API_METER_DATA_URL = f"{API_BASE_URL}/MeterData/GetTimeSeries"

DEFAULT_SCAN_INTERVAL = 3600  # 1 hour
DEFAULT_HISTORY_DAYS = 7

ATTRIBUTION = "Data provided by Eloverblik (Energinet)"
