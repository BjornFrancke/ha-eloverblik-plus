# Eloverblik Plus

Home Assistant custom integration for fetching Danish electricity consumption data
from Eloverblik / Energinet.

## Features

- Config flow setup from the Home Assistant UI
- Uses your Eloverblik refresh token and auto-discovers available metering points
- Fetches hourly consumption data from the Eloverblik API
- Exposes a sensor for the latest hourly consumption reading
- Ships a bundled Lovelace card for inspecting API-timestamped hourly points
- Preserves the fetched hourly points with start/end timestamps
- Imports hourly consumption into Home Assistant statistics for native history use
- Supports reauthentication when your refresh token changes

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install `Eloverblik Plus`.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/eloverblik_plus` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.

## Configuration

Add the integration from the Home Assistant UI:

1. Go to `Settings -> Devices & services`.
2. Choose `Add integration`.
3. Search for `Eloverblik Plus`.
4. Enter your Eloverblik refresh token.
5. If your account has access to multiple metering points, choose the one you
   want to import.

You can get your refresh token from [eloverblik.dk](https://eloverblik.dk).

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

`api_start_utc` and `api_end_utc` always reflect the raw API hour boundaries in
UTC. The `start` and `end` fields are converted into the timezone configured in
Home Assistant.

## Dashboard Card

This integration ships with a bundled Lovelace custom card that plots hourly
consumption using `hourly_data[*].api_start_utc` on the x-axis. This is the
recommended UI for inspecting API-timestamped points because the stock Home
Assistant entity popup graph still reflects recorder/history semantics.

In most storage-mode Lovelace setups the card resource is registered
automatically. If Home Assistant does not pick it up automatically, add the
resource manually:

```yaml
url: /eloverblik_plus/eloverblik-hourly-card.js
type: module
```

Then add the card to a dashboard:

```yaml
type: custom:eloverblik-hourly-card
entity: sensor.eloverblik_plus_571313174200000000_latest_hourly_consumption
title: Eloverblik Hourly API Data
hours_to_show: 24
```

The card also exposes a visual editor in Lovelace and will try to preselect the
first matching Eloverblik consumption entity automatically.

Card behavior:

- Reads the `hourly_data` attribute from `Latest hourly consumption`
- Uses `api_start_utc` as the plotted timestamp for each point
- Shows local start and local end timestamps in the hover tooltip using Home
  Assistant's configured timezone
- Defaults to the latest 24 hourly points, configurable with `hours_to_show`
- Includes an on-card dropdown to switch the visible hour range quickly

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

## Publishing Releases

For HACS, publish versioned GitHub releases so updates are easy to detect and
install.

Recommended workflow:

1. Update `custom_components/eloverblik_plus/manifest.json` and bump the
   `"version"` value, for example from `0.1.0` to `0.1.1`.
2. Commit the change.
3. Create an annotated git tag that matches the release version, usually with a
   leading `v`, for example `v0.1.1`.
4. Push the branch and tag to GitHub.
5. Create a GitHub Release from that tag.

Example:

```bash
git add custom_components/eloverblik_plus/manifest.json README.md hacs.json
git commit -m "Prepare v0.1.1 release"
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin main
git push origin v0.1.1
```

Notes:

- Keep `manifest.json` version and release tag aligned, for example
  `0.1.1` in the manifest and `v0.1.1` as the git tag
- Do not move or reuse old tags after publishing; create a new version instead
- Use patch releases like `0.1.1` for fixes and minor releases like `0.2.0`
  for new features
