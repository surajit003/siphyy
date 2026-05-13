"""Tests for the Trakzee adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from siphyy.adapters import TrakzeeAdapter
from siphyy.schema import TelemetryReading


class TestTrakzeeAdapter:
    def test_emits_telemetry_reading_for_valid_row(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        events = list(adapter.adapt([trakzee_sample_row]))
        assert len(events) == 1
        assert isinstance(events[0], TelemetryReading)

    def test_vehicle_id_defaults_to_imei_prefixed(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.vehicle_id == "trakzee:353201358420054"

    def test_vehicle_id_mapping_overrides(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter(vehicle_id_mapping={"353201358420054": "siphyy-uuid-abc"})
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.vehicle_id == "siphyy-uuid-abc"

    def test_odometer_converted_meters_to_km(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.odometer_km == 19501.664

    def test_timestamp_converted_local_to_utc(self, trakzee_sample_row: dict) -> None:
        # Trakzee export said "29-04-2026 15:48:38" in CAT (UTC+2)
        # Expect: 2026-04-29 13:48:38 UTC
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.timestamp == datetime(2026, 4, 29, 13, 48, 38, tzinfo=UTC)

    def test_status_mapped_to_engine_state(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.engine_state == "running"

    def test_ignition_parsed(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.ignition_on is True

    def test_ble_fuel_captured_in_provider_extras(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.provider_extras.get("auxiliary_channels") == [
            {"port_name": "BLE Fuel Level 1", "value": 3597}
        ]

    def test_location_text_preserved(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.location_text is not None
        assert "Lusaka" in event.location_text

    def test_missing_data_becomes_none(self, trakzee_missing_data_row: dict) -> None:
        """`--` and `NA` placeholders must become None, never fabricated."""
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_missing_data_row])))
        assert event.speed_kmh is None
        assert event.latitude is None
        assert event.longitude is None
        assert event.odometer_km is None

    def test_skips_row_without_imei(self) -> None:
        adapter = TrakzeeAdapter()
        events = list(adapter.adapt([{"Imeino": ""}]))
        assert events == []

    def test_skips_row_without_timestamp(self) -> None:
        adapter = TrakzeeAdapter()
        events = list(adapter.adapt([{"Imeino": "x", "GPSActualTime": "--"}]))
        assert events == []

    def test_provider_event_id_deterministic(self, trakzee_sample_row: dict) -> None:
        """Same input should produce the same event ID (for dedup)."""
        adapter = TrakzeeAdapter()
        events_1 = list(adapter.adapt([trakzee_sample_row]))
        events_2 = list(adapter.adapt([trakzee_sample_row]))
        assert events_1[0].provider_event_id == events_2[0].provider_event_id

    def test_provider_field_set_correctly(self, trakzee_sample_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.provider == "trakzee"

    def test_non_dict_inputs_skipped(self) -> None:
        adapter = TrakzeeAdapter()
        events = list(adapter.adapt(["not a dict", None, 42]))  # type: ignore[list-item]
        assert events == []
