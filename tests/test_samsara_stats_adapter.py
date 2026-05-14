"""Tests for the Samsara stats/history adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from siphyy.adapters import SamsaraStatsAdapter
from siphyy.schema import TelemetryReading


class TestSamsaraStatsAdapter:
    def test_emits_one_reading_per_unique_timestamp(self, samsara_stats_payload: dict) -> None:
        """The fixture has GPS at 10 timestamps, fuel at 11, odometer at 3.
        Union of timestamps (some shared) gives 11 unique points → 11
        readings for the single vehicle."""
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        assert len(events) == 11
        assert all(isinstance(e, TelemetryReading) for e in events)

    def test_speed_converts_mph_to_kmh(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        # 07:08 row: 28 mph → 45.06 km/h
        event = next(e for e in events if e.timestamp == datetime(2026, 4, 29, 7, 8, tzinfo=UTC))
        assert event.speed_kmh is not None
        assert abs(event.speed_kmh - 28 * 1.609344) < 1e-9

    def test_odometer_converts_meters_to_km(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        # 06:12: obdOdometerMeters = 142840000 → 142840 km
        event = next(e for e in events if e.timestamp == datetime(2026, 4, 29, 6, 12, tzinfo=UTC))
        assert event.odometer_km == 142840.0

    def test_fuel_percent_maps_directly(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        event = next(e for e in events if e.timestamp == datetime(2026, 4, 29, 6, 12, tzinfo=UTC))
        assert event.fuel_level_percent == 78.0
        # Also mirrored into fuel_level_raw so the reference detector — which
        # reads only that field — can fire on Samsara data unchanged. See
        # PR notes for the schema-friction analysis.
        assert event.fuel_level_raw == 78.0

    def test_engine_state_on_maps_to_running(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        # engineStates: On at 06:10 → 06:12 reading should be running.
        event = next(e for e in events if e.timestamp == datetime(2026, 4, 29, 6, 12, tzinfo=UTC))
        assert event.engine_state == "running"
        assert event.ignition_on is True

    def test_engine_state_off_maps_to_stopped(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        # engineStates: Off at 17:18 → 17:20 reading should be stopped.
        event = next(e for e in events if e.timestamp == datetime(2026, 4, 29, 17, 20, tzinfo=UTC))
        assert event.engine_state == "stopped"
        assert event.ignition_on is False

    def test_engine_state_forward_fills_to_later_timestamps(
        self, samsara_stats_payload: dict
    ) -> None:
        """01:30 next day has fuel data but no GPS or engine-state entry.
        Engine state should be carried forward from the last transition
        (Off at 17:18)."""
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        overnight = next(
            e for e in events if e.timestamp == datetime(2026, 4, 30, 1, 30, tzinfo=UTC)
        )
        assert overnight.engine_state == "stopped"
        assert overnight.ignition_on is False
        # No GPS at this timestamp — only fuel is present.
        assert overnight.latitude is None
        assert overnight.longitude is None
        assert overnight.speed_kmh is None
        assert overnight.fuel_level_percent == 10.0

    def test_location_text_from_reverse_geo(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        event = next(e for e in events if e.timestamp == datetime(2026, 4, 29, 6, 12, tzinfo=UTC))
        assert event.location_text == "Apapa Depot, Lagos"

    def test_vehicle_id_defaults_to_samsara_prefixed(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events = list(adapter.adapt(samsara_stats_payload))
        assert all(e.vehicle_id == "samsara:281474977345001" for e in events)

    def test_vehicle_id_mapping_overrides(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter(vehicle_id_mapping={"281474977345001": "siphyy-uuid-7"})
        events = list(adapter.adapt(samsara_stats_payload))
        assert all(e.vehicle_id == "siphyy-uuid-7" for e in events)

    def test_empty_data_yields_no_events(self) -> None:
        adapter = SamsaraStatsAdapter()
        assert list(adapter.adapt({"data": []})) == []
        assert list(adapter.adapt({})) == []

    def test_missing_optional_fields_dont_crash(self) -> None:
        """Sparse payload — vehicle has only fuel data, no GPS / odometer /
        engine state. The adapter should still emit a reading with fuel
        and everything else None."""
        adapter = SamsaraStatsAdapter()
        payload = {
            "data": [
                {
                    "id": "vehicle-x",
                    "fuelPercents": [{"time": "2026-04-29T12:00:00Z", "value": 55.0}],
                }
            ]
        }
        events = list(adapter.adapt(payload))
        assert len(events) == 1
        event = events[0]
        assert event.fuel_level_percent == 55.0
        assert event.latitude is None
        assert event.engine_state is None
        assert event.odometer_km is None

    def test_skips_vehicle_without_id(self) -> None:
        adapter = SamsaraStatsAdapter()
        payload = {"data": [{"name": "no-id-vehicle", "gps": [{"time": "2026-04-29T12:00:00Z"}]}]}
        assert list(adapter.adapt(payload)) == []

    def test_provider_extras_includes_external_ids_and_name(
        self, samsara_stats_payload: dict
    ) -> None:
        adapter = SamsaraStatsAdapter()
        event = next(iter(adapter.adapt(samsara_stats_payload)))
        assert event.provider_extras["name"] == "Lagos Truck 7"
        external_ids = event.provider_extras["externalIds"]
        assert isinstance(external_ids, dict)
        assert external_ids["samsara.vin"] == "JTMBK32V895099731"

    def test_provider_field_is_samsara(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        event = next(iter(adapter.adapt(samsara_stats_payload)))
        assert event.provider == "samsara"

    def test_provider_event_id_deterministic(self, samsara_stats_payload: dict) -> None:
        adapter = SamsaraStatsAdapter()
        events_a = list(adapter.adapt(samsara_stats_payload))
        events_b = list(adapter.adapt(samsara_stats_payload))
        assert [e.provider_event_id for e in events_a] == [e.provider_event_id for e in events_b]

    def test_non_dict_input_yields_no_events(self) -> None:
        adapter = SamsaraStatsAdapter()
        assert list(adapter.adapt(["not a dict"])) == []  # type: ignore[list-item]
