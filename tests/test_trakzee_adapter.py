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
        """Raw auxiliary channels are still preserved for multi-sensor cases
        and traceability, even though the primary reading is promoted."""
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.provider_extras.get("auxiliary_channels") == [
            {"port_name": "BLE Fuel Level 1", "value": 3597}
        ]

    def test_ble_fuel_promoted_to_canonical_fields(self, trakzee_sample_row: dict) -> None:
        """The detector tier reads fuel_level_raw, not provider_extras."""
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.fuel_level_raw == 3597.0
        assert event.fuel_sensor_type == "ble"

    def test_calibrated_fuel_fields_left_none_without_calibration(
        self, trakzee_sample_row: dict
    ) -> None:
        """Trakzee BLE readings are raw counts. Without per-vehicle calibration
        the adapter must not fabricate percent/liters."""
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_sample_row])))
        assert event.fuel_level_percent is None
        assert event.fuel_level_liters is None
        assert event.tank_capacity_liters is None

    def test_fuel_fields_none_when_no_aux_channels(self, trakzee_missing_data_row: dict) -> None:
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([trakzee_missing_data_row])))
        assert event.fuel_level_raw is None
        assert event.fuel_sensor_type is None
        assert event.fuel_level_percent is None
        assert event.fuel_level_liters is None

    def test_picks_first_ble_fuel_in_multi_sensor_row(self, trakzee_sample_row: dict) -> None:
        """Multi-sensor trucks report multiple BLE channels; the canonical
        record carries the first one, the rest stay in provider_extras."""
        row = dict(trakzee_sample_row)
        row["Fuel"] = (
            '[{"port_name": "BLE Fuel Level 1", "value": 3597},'
            ' {"port_name": "BLE Fuel Level 2", "value": 1820}]'
        )
        adapter = TrakzeeAdapter()
        event = next(iter(adapter.adapt([row])))
        assert event.fuel_level_raw == 3597.0
        # All channels are still available for callers that want them.
        assert event.provider_extras["auxiliary_channels"] == [
            {"port_name": "BLE Fuel Level 1", "value": 3597},
            {"port_name": "BLE Fuel Level 2", "value": 1820},
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
