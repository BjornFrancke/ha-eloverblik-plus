# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration for **Eloverblik** (Danish electricity data from Energinet). Domain: `eloverblik_plus`. Fetches hourly consumption data from the Eloverblik API using a refresh token and metering point ID.

## Commands

```bash
# Activate venv
source venv/bin/activate

# Run all tests
pytest

# Run a single test file
pytest tests/test_config_flow.py

# Run a single test
pytest tests/test_config_flow.py::test_user_flow_success -v

# Lint
ruff check custom_components/ tests/

# Format
ruff format custom_components/ tests/

# Auto-fix lint issues
ruff check --fix custom_components/ tests/

# Run HA for manual testing (config dir included in repo)
hass -c config/
```

## Architecture

Standard HA custom component pattern with config flow + coordinator:

- **`api.py`** — Async API client (`EloverblikApiClient`). Handles token exchange (refresh → access) and time series fetching from `api.eloverblik.dk`. Custom exception hierarchy: `EloverblikError` → `EloverblikAuthError` / `EloverblikConnectionError`.
- **`coordinator.py`** — `DataUpdateCoordinator` subclass. Polls `async_get_latest_consumption()` every hour. Maps `EloverblikAuthError` → `ConfigEntryAuthFailed`, other errors → `UpdateFailed`.
- **`sensor.py`** — Single `SensorEntity` per metering point. Reports `total_kwh` as state, hourly breakdown in `extra_state_attributes`. Uses `SensorStateClass.TOTAL_INCREASING`.
- **`config_flow.py`** — User step validates credentials by calling `async_get_access_token()`. Deduplicates by metering point ID (`async_set_unique_id`).
- **`__init__.py`** — Entry setup/teardown. Stores `EloverblikData(client, coordinator)` as `entry.runtime_data`. Uses `ConfigEntry[EloverblikData]` type alias.

## Testing

Tests use `pytest-homeassistant-custom-component` which provides the `hass` fixture and `enable_custom_integrations`. The API client is mocked via `unittest.mock.patch` — see `tests/conftest.py` for shared fixtures and mock data constants. Tests run with `asyncio_mode = "auto"`.

## Key Conventions

- Python 3.12+ (`from __future__ import annotations` everywhere)
- Ruff for linting/formatting (line-length 88, rules: B/E/F/I/SIM/UP/W)
- Config uses `CONF_REFRESH_TOKEN` and `CONF_METERING_POINT` (defined in `const.py`)
- API response structure: `result[0].MyEnergyData_MarketDocument.TimeSeries[0].Period[-1].Point[]`
