"""Tests for the canonical event schema."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from siphyy.schema import (
    DriverEvent,
    TelemetryReading,
)


class TestTelemetryReading:
    def test_minimal_valid_event(self) -> None:
        event = TelemetryReading(
            vehicle_id="canonical:vehicle_1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
        )
        assert event.event_type == "telemetry"
        assert event.schema_version == "1.0"
        assert event.latitude is None  # all optional fields default to None

    def test_full_event(self) -> None:
        event = TelemetryReading(
            vehicle_id="canonical:vehicle_1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
            latitude=-15.38,
            longitude=28.21,
            speed_kmh=45.5,
            engine_state="running",
            ignition_on=True,
            odometer_km=19501.664,
        )
        assert event.speed_kmh == 45.5
        assert event.engine_state == "running"

    def test_speed_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TelemetryReading(
                vehicle_id="v1",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                provider="test",
                speed_kmh=-5.0,
            )

    def test_battery_percent_bounded(self) -> None:
        with pytest.raises(ValidationError):
            TelemetryReading(
                vehicle_id="v1",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                provider="test",
                battery_percent=150.0,
            )

    def test_immutable(self) -> None:
        event = TelemetryReading(
            vehicle_id="v1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
        )
        with pytest.raises(ValidationError):
            event.speed_kmh = 100  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Schema is closed — typos should be caught, not silently accepted."""
        with pytest.raises(ValidationError, match="extra"):
            TelemetryReading(
                vehicle_id="v1",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                provider="test",
                speedd_kmh=45.5,  # typo  # type: ignore[call-arg]
            )


class TestDriverEvent:
    def test_harsh_brake(self) -> None:
        event = DriverEvent(
            vehicle_id="v1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
            subtype="harsh_brake",
            g_force=0.55,
        )
        assert event.event_type == "driver_event"
        assert event.subtype == "harsh_brake"


class TestCanonicalEventDiscrimination:
    """The discriminated union should route on `event_type`."""

    def test_telemetry_round_trip(self) -> None:
        event = TelemetryReading(
            vehicle_id="v1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
        )
        # Round-trip through JSON should preserve the discriminator
        json_str = event.model_dump_json()
        assert '"event_type":"telemetry"' in json_str

    def test_driver_event_round_trip(self) -> None:
        event = DriverEvent(
            vehicle_id="v1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
            subtype="harsh_brake",
        )
        json_str = event.model_dump_json()
        assert '"event_type":"driver_event"' in json_str
