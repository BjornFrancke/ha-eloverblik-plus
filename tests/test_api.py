"""Tests for the Eloverblik API client parsing."""

from __future__ import annotations

from custom_components.eloverblik_custom.api import EloverblikApiClient

from .conftest import MOCK_TIME_SERIES_RESPONSE


def test_parse_time_series_multi_period() -> None:
    """Test parsing a response with multiple periods."""
    result = EloverblikApiClient._parse_time_series(MOCK_TIME_SERIES_RESPONSE)

    assert result["total_kwh"] == 2.0
    assert len(result["hourly"]) == 5
    assert result["hourly"][0] == {"timestamp": "2024-01-01T00:00:00", "kwh": 0.5}
    assert result["hourly"][3] == {"timestamp": "2024-01-02T00:00:00", "kwh": 0.4}

    assert result["daily"] == {
        "2024-01-01": 1.0,
        "2024-01-02": 1.0,
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
                "MyEnergyData_MarketDocument": {
                    "TimeSeries": [
                        {
                            "Period": [
                                {
                                    "timeInterval": {
                                        "start": "2024-03-15T00:00:00Z",
                                        "end": "2024-03-16T00:00:00Z",
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
                }
            }
        ]
    }
    result = EloverblikApiClient._parse_time_series(data)

    assert result["total_kwh"] == 4.0
    assert len(result["hourly"]) == 2
    assert result["daily"] == {"2024-03-15": 4.0}


def test_parse_time_series_rounding() -> None:
    """Test that totals are properly rounded."""
    data = {
        "result": [
            {
                "MyEnergyData_MarketDocument": {
                    "TimeSeries": [
                        {
                            "Period": [
                                {
                                    "timeInterval": {
                                        "start": "2024-01-01T00:00:00Z",
                                        "end": "2024-01-02T00:00:00Z",
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
                }
            }
        ]
    }
    result = EloverblikApiClient._parse_time_series(data)

    assert result["total_kwh"] == 0.999
    assert result["daily"]["2024-01-01"] == 0.999
