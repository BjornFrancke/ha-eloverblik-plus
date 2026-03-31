# Eloverblik Custom

Home Assistant custom integration for fetching Danish electricity consumption data
from Eloverblik / Energinet.

## Features

- Config flow setup from the Home Assistant UI
- Uses your Eloverblik refresh token and metering point ID
- Fetches hourly consumption data from the Eloverblik API
- Exposes a sensor with total consumption plus hourly and daily breakdowns
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

The integration creates one sensor per metering point:

- `Energy consumption`

The sensor includes extra attributes:

- `metering_point`
- `hourly_data`
- `daily_data`

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
