# Eloverblik Custom

Home Assistant custom integration for fetching Danish electricity consumption data
from Eloverblik / Energinet.

## Features

- Config flow setup from the Home Assistant UI
- Uses your Eloverblik refresh token and metering point ID
- Fetches hourly consumption data from the Eloverblik API
- Exposes a sensor for the latest hourly consumption reading
- Preserves the fetched hourly points with start/end timestamps
- Imports hourly consumption into Home Assistant statistics for native history use
- Supports reauthentication when your refresh token changes

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install `Eloverblik Custom`.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/eloverblik_custom` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.

## Configuration

Add the integration from the Home Assistant UI:

1. Go to `Settings -> Devices & services`.
2. Choose `Add integration`.
3. Search for `Eloverblik Custom`.
4. Enter:
   - Your Eloverblik refresh token
   - Your metering point ID

You can get your refresh token and metering point information from
[eloverblik.dk](https://eloverblik.dk).

## Data Exposed

The integration creates two sensors per metering point:

- `Latest hourly consumption`
- `Latest hourly interval start`

`Latest hourly consumption` includes extra attributes:

- `metering_point`
- `latest_hour_api_start_utc`
- `latest_hour_api_end_utc`
- `latest_hour_start`
- `latest_hour_end`
- `window_total_kwh`
- `hourly_data`
- `daily_data`

`Latest hourly interval start` is a timestamp sensor that surfaces the API hour
used for the latest reading directly in Home Assistant. Its attributes include:

- `api_end_utc`
- `local_start`
- `local_end`

`hourly_data` contains the fetched Eloverblik interval points exactly as hourly
readings with `api_start_utc`, `api_end_utc`, `start`, `end`, and `kwh`
fields. The integration also imports those hourly points into Home Assistant
statistics using a stable external statistics ID so they can be graphed and
reused natively by Home Assistant.

## Development

Run the test suite:

```bash
pytest
```

Run linting:

```bash
ruff check custom_components/ tests/
ruff format --check custom_components/ tests/
```
