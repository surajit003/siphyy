"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def trakzee_sample_row() -> dict:
    """One realistic Trakzee positions row, as produced by their export."""
    return {
        "fetched_at": "2026-04-29T16:49:52",
        "Imeino": "353201358420054",
        "Vehicle_No": "BCG 8420 (COMPANY)",
        "Vehicle_Name": "BCG 8420",
        "Company": "ZM Pepsi",
        "Branch": "Milk Tanker",
        "Vehicletype": "Minitruck",
        "DeviceModel": "FMB920",
        "Status": "RUNNING",
        "Power": "ON",
        "IGN": "ON",
        "GPS": "ON",
        "Speed": "0",
        "Angle": "301",
        "Odometer": "19501664",
        "Latitude": "-15.3838966",
        "Longitude": "28.208965",
        "Location": "George,Lusaka,Lusaka District,10101, Lusaka Province, Zambia (SW)",
        "POI": "--",
        "GPSActualTime": "29-04-2026 15:48:38",
        "Datetime": "29-04-2026 15:48:49",
        "ExternalVolt": "28.12",
        "battery_percentage": "0",
        "satellite_count": "14",
        "gps_hdop": "NA",
        "Fuel": '[{"port_name": "BLE Fuel Level 1", "value": 3597}]',
        "AC": "--",
        "Altitude": "1261",
    }


@pytest.fixture
def trakzee_missing_data_row() -> dict:
    """A row with lots of '--' and 'NA' values, to exercise null-handling."""
    return {
        "Imeino": "353201358287644",
        "Vehicle_Name": "BCA 4676",
        "Status": "STOP",
        "IGN": "OFF",
        "Speed": "--",
        "Latitude": "--",
        "Longitude": "--",
        "Odometer": "NA",
        "GPSActualTime": "29-04-2026 15:47:36",
        "ExternalVolt": "12.87",
        "Fuel": "[]",
        "AC": "--",
        "Altitude": "1280",
    }
