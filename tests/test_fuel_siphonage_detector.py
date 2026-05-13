"""Tests for the FuelSiphonageDetector."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from siphyy.detectors import FuelSiphonageDetector, InMemoryStateStore
from siphyy.schema import DriverEvent, EngineState, TelemetryReading


def _reading(
    *,
    vehicle_id: str = "v1",
    minute_offset: int = 0,
    fuel_level_raw: float | None = 3597.0,
    engine_state: EngineState | None = "stopped",
    ignition_on: bool | None = False,
    provider_event_id: str | None = None,
    altitude_m: float | None = None,
    pitch_deg: float | None = None,
    roll_deg: float | None = None,
) -> TelemetryReading:
    return TelemetryReading(
        vehicle_id=vehicle_id,
        timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC) + timedelta(minutes=minute_offset),
        provider="test",
        provider_event_id=provider_event_id,
        fuel_level_raw=fuel_level_raw,
        fuel_sensor_type="ble",
        engine_state=engine_state,
        ignition_on=ignition_on,
        altitude_m=altitude_m,
        pitch_deg=pitch_deg,
        roll_deg=roll_deg,
    )


class TestFuelSiphonageDetector:
    def test_first_event_never_fires(self) -> None:
        detector = FuelSiphonageDetector()
        result = detector.process(_reading(fuel_level_raw=3000.0))
        assert result is None

    def test_drop_while_engine_off_fires(self) -> None:
        detector = FuelSiphonageDetector()
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        result = detector.process(_reading(minute_offset=10, fuel_level_raw=2000.0))
        assert result is not None
        assert result.category == "fuel_drop"
        assert result.detector_name == "fuel_siphonage"
        assert result.evidence["drop_pct"] == pytest.approx(1000.0 / 3000.0, rel=1e-3)
        assert result.evidence["prior_fuel_level_raw"] == 3000.0
        assert result.evidence["current_fuel_level_raw"] == 2000.0

    def test_no_fire_when_engine_running(self) -> None:
        detector = FuelSiphonageDetector()
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        result = detector.process(
            _reading(minute_offset=10, fuel_level_raw=2000.0, engine_state="running")
        )
        assert result is None

    def test_no_fire_when_ignition_on(self) -> None:
        detector = FuelSiphonageDetector()
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        result = detector.process(
            _reading(minute_offset=10, fuel_level_raw=2000.0, ignition_on=True)
        )
        assert result is None

    def test_no_fire_when_drop_below_threshold(self) -> None:
        detector = FuelSiphonageDetector(threshold_pct=0.20)
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        # 10% drop, threshold is 20%.
        result = detector.process(_reading(minute_offset=10, fuel_level_raw=2700.0))
        assert result is None

    def test_no_fire_when_window_exceeded(self) -> None:
        detector = FuelSiphonageDetector(max_minutes=30)
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        result = detector.process(_reading(minute_offset=120, fuel_level_raw=2000.0))
        assert result is None

    def test_no_fire_on_out_of_order_events(self) -> None:
        detector = FuelSiphonageDetector()
        detector.process(_reading(minute_offset=30, fuel_level_raw=3000.0))
        # Earlier event arriving after a later one — elapsed becomes negative.
        result = detector.process(_reading(minute_offset=10, fuel_level_raw=2000.0))
        assert result is None

    def test_no_fire_on_increase(self) -> None:
        """Refuel events should not be misclassified as drops."""
        detector = FuelSiphonageDetector()
        detector.process(_reading(minute_offset=0, fuel_level_raw=2000.0))
        result = detector.process(_reading(minute_offset=10, fuel_level_raw=3000.0))
        assert result is None

    def test_no_fire_on_missing_fuel_data(self) -> None:
        detector = FuelSiphonageDetector()
        result = detector.process(_reading(fuel_level_raw=None))
        assert result is None

    def test_no_fire_on_driver_event(self) -> None:
        detector = FuelSiphonageDetector()
        ev = DriverEvent(
            vehicle_id="v1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            provider="test",
            subtype="harsh_brake",
        )
        assert detector.process(ev) is None

    def test_severity_scales_with_drop_magnitude(self) -> None:
        detector = FuelSiphonageDetector()
        # 20% drop -> medium
        detector.process(_reading(vehicle_id="a", minute_offset=0, fuel_level_raw=1000.0))
        medium = detector.process(_reading(vehicle_id="a", minute_offset=5, fuel_level_raw=800.0))
        assert medium is not None and medium.severity == "medium"

        # 30% drop -> high
        detector.process(_reading(vehicle_id="b", minute_offset=0, fuel_level_raw=1000.0))
        high = detector.process(_reading(vehicle_id="b", minute_offset=5, fuel_level_raw=700.0))
        assert high is not None and high.severity == "high"

        # 50% drop -> critical
        detector.process(_reading(vehicle_id="c", minute_offset=0, fuel_level_raw=1000.0))
        crit = detector.process(_reading(vehicle_id="c", minute_offset=5, fuel_level_raw=500.0))
        assert crit is not None and crit.severity == "critical"

    def test_state_isolated_per_vehicle(self) -> None:
        """A drop on vehicle A must not trigger a fire on vehicle B."""
        detector = FuelSiphonageDetector()
        detector.process(_reading(vehicle_id="a", minute_offset=0, fuel_level_raw=3000.0))
        # First reading for B — no baseline, must not fire even with a "drop"-shaped pair.
        result = detector.process(_reading(vehicle_id="b", minute_offset=10, fuel_level_raw=1000.0))
        assert result is None

    def test_triggering_event_id_propagates(self) -> None:
        detector = FuelSiphonageDetector()
        detector.process(
            _reading(minute_offset=0, fuel_level_raw=3000.0, provider_event_id="evt-1")
        )
        result = detector.process(
            _reading(minute_offset=10, fuel_level_raw=2000.0, provider_event_id="evt-2")
        )
        assert result is not None
        assert result.triggering_event_id == "evt-2"

    def test_explicit_state_store_is_used(self) -> None:
        store = InMemoryStateStore()
        detector = FuelSiphonageDetector(state_store=store)
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        assert store.get("fuel_siphonage:v1") is not None

    def test_orientation_evidence_included_when_present(self) -> None:
        """Slope context flows into evidence so the agent can reason about
        post-climb settling and parked-on-incline false positives."""
        detector = FuelSiphonageDetector()
        detector.process(
            _reading(
                minute_offset=0,
                fuel_level_raw=3000.0,
                altitude_m=1180.0,
                pitch_deg=6.5,
            )
        )
        result = detector.process(
            _reading(
                minute_offset=10,
                fuel_level_raw=2000.0,
                altitude_m=1275.0,
                pitch_deg=0.5,
                roll_deg=-1.2,
            )
        )

        assert result is not None
        assert result.evidence["prior_altitude_m"] == 1180.0
        assert result.evidence["current_altitude_m"] == 1275.0
        assert result.evidence["altitude_delta_m"] == 95.0
        assert result.evidence["prior_pitch_deg"] == 6.5
        assert result.evidence["current_pitch_deg"] == 0.5
        assert result.evidence["current_roll_deg"] == -1.2

    def test_orientation_evidence_omitted_when_unknown(self) -> None:
        """Evidence stays clean — no None-valued keys — when the provider
        doesn't supply orientation data."""
        detector = FuelSiphonageDetector()
        detector.process(_reading(minute_offset=0, fuel_level_raw=3000.0))
        result = detector.process(_reading(minute_offset=10, fuel_level_raw=2000.0))

        assert result is not None
        assert "current_altitude_m" not in result.evidence
        assert "prior_altitude_m" not in result.evidence
        assert "altitude_delta_m" not in result.evidence
        assert "current_pitch_deg" not in result.evidence
        assert "current_roll_deg" not in result.evidence
