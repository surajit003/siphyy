"""Tests for the Samsara webhook adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from siphyy.adapters import SamsaraWebhookAdapter
from siphyy.schema import DriverEvent


class TestSamsaraWebhookAdapter:
    def test_harsh_braking_emits_harsh_brake_event(self, samsara_webhook_payloads: dict) -> None:
        adapter = SamsaraWebhookAdapter()
        events = list(adapter.adapt([samsara_webhook_payloads["harsh_braking_event"]]))
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DriverEvent)
        assert event.subtype == "harsh_brake"
        assert event.vehicle_id == "samsara:281474977345001"
        assert event.timestamp == datetime(2026, 4, 29, 8, 42, 13, tzinfo=UTC)
        assert event.latitude == 6.5612
        assert event.longitude == 3.3702

    def test_harsh_acceleration_emits_harsh_accel_event(
        self, samsara_webhook_payloads: dict
    ) -> None:
        adapter = SamsaraWebhookAdapter()
        events = list(adapter.adapt([samsara_webhook_payloads["harsh_acceleration_event"]]))
        assert len(events) == 1
        assert events[0].subtype == "harsh_accel"

    def test_speeding_alert_emits_speeding_event(self, samsara_webhook_payloads: dict) -> None:
        adapter = SamsaraWebhookAdapter()
        events = list(adapter.adapt([samsara_webhook_payloads["speeding_alert"]]))
        assert len(events) == 1
        event = events[0]
        assert event.subtype == "speeding"
        # No g-force on speeding events — spec is explicit about this.
        assert event.g_force is None

    def test_geofence_exit_alert_skipped(self, samsara_webhook_payloads: dict) -> None:
        adapter = SamsaraWebhookAdapter()
        events = list(adapter.adapt([samsara_webhook_payloads["geofence_exit_alert"]]))
        assert events == []

    def test_speed_converts_mph_to_kmh_in_provider_extras(
        self, samsara_webhook_payloads: dict
    ) -> None:
        adapter = SamsaraWebhookAdapter()
        speeding = next(iter(adapter.adapt([samsara_webhook_payloads["speeding_alert"]])))
        # 58 mph in payload → ~93.34 km/h. Canonical schema has no speed
        # field on DriverEvent (it's for telemetry, not events), so the
        # converted value lands in provider_extras.
        assert abs(speeding.provider_extras["speed_kmh"] - 58 * 1.609344) < 1e-9  # type: ignore[operator]
        assert speeding.provider_extras["speed_mph"] == 58.0
        assert abs(speeding.provider_extras["speed_limit_kmh"] - 50 * 1.609344) < 1e-9  # type: ignore[operator]

        harsh = next(iter(adapter.adapt([samsara_webhook_payloads["harsh_braking_event"]])))
        # Harsh-event payload uses speedAtTimeOfIncidentMilesPerHour=38.
        assert harsh.provider_extras["speed_mph"] == 38.0

    def test_vehicle_id_default_prefixed(self, samsara_webhook_payloads: dict) -> None:
        adapter = SamsaraWebhookAdapter()
        event = next(iter(adapter.adapt([samsara_webhook_payloads["harsh_braking_event"]])))
        assert event.vehicle_id == "samsara:281474977345001"

    def test_vehicle_id_mapping_overrides(self, samsara_webhook_payloads: dict) -> None:
        adapter = SamsaraWebhookAdapter(vehicle_id_mapping={"281474977345001": "siphyy-uuid-7"})
        event = next(iter(adapter.adapt([samsara_webhook_payloads["harsh_braking_event"]])))
        assert event.vehicle_id == "siphyy-uuid-7"

    def test_provider_event_id_from_webhook_event_id(self, samsara_webhook_payloads: dict) -> None:
        adapter = SamsaraWebhookAdapter()
        event = next(iter(adapter.adapt([samsara_webhook_payloads["harsh_braking_event"]])))
        assert event.provider_event_id == "a9db46da-7519-4aca-92af-0cb533d5862e"

    def test_unknown_event_type_skipped(self) -> None:
        adapter = SamsaraWebhookAdapter()
        bogus = {
            "eventId": "abc",
            "eventType": "SomeThingWeDoNotHandle",
            "eventTime": "2026-04-29T12:00:00Z",
            "data": {"vehicle": {"id": "1"}},
        }
        assert list(adapter.adapt([bogus])) == []

    def test_alert_with_unknown_condition_skipped(self) -> None:
        adapter = SamsaraWebhookAdapter()
        bogus = {
            "eventId": "abc",
            "eventType": "Alert",
            "eventTime": "2026-04-29T12:00:00Z",
            "data": {
                "alertConditionId": "SomeUnknownCondition",
                "vehicle": {"id": "1"},
            },
        }
        assert list(adapter.adapt([bogus])) == []

    def test_non_dict_payloads_skipped(self) -> None:
        adapter = SamsaraWebhookAdapter()
        assert list(adapter.adapt(["string", None, 42])) == []  # type: ignore[list-item]

    def test_processes_all_payloads_from_fixture(self, samsara_webhook_payloads: dict) -> None:
        """Smoke-test: feed all four fixture payloads at once. Expect three
        events (geofence is skipped)."""
        adapter = SamsaraWebhookAdapter()
        events = list(adapter.adapt(samsara_webhook_payloads.values()))
        subtypes = {e.subtype for e in events}
        assert subtypes == {"harsh_brake", "harsh_accel", "speeding"}
