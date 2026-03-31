"""Tests for the Eloverblik API client."""

from __future__ import annotations

import pytest

from custom_components.eloverblik_custom.api import EloverblikApiClient, EloverblikError

from .conftest import MOCK_TIME_SERIES_RESPONSE


def test_parse_time_series_multi_period() -> None:
    """Test parsing a response with multiple periods."""
    result = EloverblikApiClient._parse_time_series(MOCK_TIME_SERIES_RESPONSE)

    assert result["total_kwh"] == 2.0
    assert len(result["hourly"]) == 5
    assert result["hourly"][0] == {
        "timestamp": "2024-01-02T00:00:00+01:00",
        "kwh": 0.5,
    }
    assert result["hourly"][3] == {
        "timestamp": "2024-01-03T00:00:00+01:00",
        "kwh": 0.4,
    }

    assert result["daily"] == {
        "2024-01-02": 1.0,
        "2024-01-03": 1.0,
    }


def test_parse_time_series_empty_result() -> None:
    """Test parsing an empty API response."""
    result = EloverblikApiClient._parse_time_series({"result": []})

    assert result == {"total_kwh": 0.0, "hourly": [], "daily": {}}


def test_parse_time_series_no_time_series() -> None:
    """Test parsing a response with no time series."""
    data = {"result": [{"MyEnergyData_MarketDocument": {"TimeSeries": []}}]}
    result = EloverblikApiClient._parse_time_series(data)

    assert result == {"total_kwh": 0.0, "hourly": [], "daily": {}}


def test_parse_time_series_no_periods() -> None:
    """Test parsing a response with empty periods."""
    data = {
        "result": [{"MyEnergyData_MarketDocument": {"TimeSeries": [{"Period": []}]}}]
    }
    result = EloverblikApiClient._parse_time_series(data)

    assert result == {"total_kwh": 0.0, "hourly": [], "daily": {}}


def test_parse_time_series_single_period() -> None:
    """Test parsing a response with a single period."""
    data = {
        "result": [
            {
                "success": True,
                "errorCode": 10000,
                "MyEnergyData_MarketDocument": {
                    "TimeSeries": [
                        {
                            "Period": [
                                {
                                    "timeInterval": {
                                        "start": "2024-03-14T23:00:00Z",
                                        "end": "2024-03-15T23:00:00Z",
                                    },
                                    "Point": [
                                        {
                                            "position": "1",
                                            "out_Quantity.quantity": "1.5",
                                        },
                                        {
                                            "position": "2",
                                            "out_Quantity.quantity": "2.5",
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                },
            }
        ]
    }
    result = EloverblikApiClient._parse_time_series(data)

    assert result["total_kwh"] == 4.0
    assert len(result["hourly"]) == 2
    assert result["hourly"][0]["timestamp"] == "2024-03-15T00:00:00+01:00"
    assert result["daily"] == {"2024-03-15": 4.0}


def test_parse_time_series_rounding() -> None:
    """Test that totals are properly rounded."""
    data = {
        "result": [
            {
                "success": True,
                "errorCode": 10000,
                "MyEnergyData_MarketDocument": {
                    "TimeSeries": [
                        {
                            "Period": [
                                {
                                    "timeInterval": {
                                        "start": "2024-01-01T23:00:00Z",
                                        "end": "2024-01-02T23:00:00Z",
                                    },
                                    "Point": [
                                        {
                                            "position": "1",
                                            "out_Quantity.quantity": "0.333",
                                        },
                                        {
                                            "position": "2",
                                            "out_Quantity.quantity": "0.333",
                                        },
                                        {
                                            "position": "3",
                                            "out_Quantity.quantity": "0.333",
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                },
            }
        ]
    }
    result = EloverblikApiClient._parse_time_series(data)

    assert result["total_kwh"] == 0.999
    assert result["daily"]["2024-01-02"] == 0.999


def test_parse_time_series_dst_day() -> None:
    """Test that DST transition days keep the correct local timestamps."""
    data = {
        "result": [
            {
                "success": True,
                "errorCode": 10000,
                "MyEnergyData_MarketDocument": {
                    "TimeSeries": [
                        {
                            "Period": [
                                {
                                    "timeInterval": {
                                        "start": "2026-03-28T23:00:00Z",
                                        "end": "2026-03-29T22:00:00Z",
                                    },
                                    "Point": [
                                        {
                                            "position": "1",
                                            "out_Quantity.quantity": "0.1",
                                        },
                                        {
                                            "position": "2",
                                            "out_Quantity.quantity": "0.2",
                                        },
                                        {
                                            "position": "3",
                                            "out_Quantity.quantity": "0.3",
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                },
            }
        ]
    }

    result = EloverblikApiClient._parse_time_series(data)

    assert result["daily"] == {"2026-03-29": 0.6}
    assert result["hourly"] == [
        {"timestamp": "2026-03-29T00:00:00+01:00", "kwh": 0.1},
        {"timestamp": "2026-03-29T01:00:00+01:00", "kwh": 0.2},
        {"timestamp": "2026-03-29T03:00:00+02:00", "kwh": 0.3},
    ]


def test_parse_time_series_raises_on_api_error() -> None:
    """Test that API-level errors are surfaced instead of parsed."""
    data = {
        "result": [
            {
                "success": False,
                "errorCode": 20001,
                "errorText": "Expired token",
                "MyEnergyData_MarketDocument": {"TimeSeries": []},
            }
        ]
    }

    with pytest.raises(EloverblikError, match="20001: Expired token"):
        EloverblikApiClient._parse_time_series(data)
