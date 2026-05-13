"""Tests for the InterestingEvent schema."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from siphyy.schema import InterestingEvent


class TestInterestingEvent:
    def test_minimal_valid(self) -> None:
        event = InterestingEvent(
            detector_name="fuel_siphonage",
            vehicle_id="v1",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            category="fuel_drop",
            severity="medium",
            summary="Fuel dropped 20% while engine off.",
            confidence=0.6,
        )
        assert event.schema_version == "1.0"
        assert event.evidence == {}
        assert event.triggering_event_id is None

    def test_full_event_round_trip(self) -> None:
        event = InterestingEvent(
            detector_name="fuel_siphonage",
            vehicle_id="trakzee:353201358420054",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            category="fuel_drop",
            severity="critical",
            summary="47% drop while parked.",
            confidence=0.7,
            evidence={"drop_pct": 0.47, "prior_fuel_level_raw": 3597},
            triggering_event_id="353201358420054:1747130918",
        )
        as_json = event.model_dump_json()
        assert '"category":"fuel_drop"' in as_json
        assert '"severity":"critical"' in as_json

    def test_confidence_bounded_above(self) -> None:
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            InterestingEvent(
                detector_name="d",
                vehicle_id="v",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                category="fuel_drop",
                severity="low",
                summary="x",
                confidence=1.5,
            )

    def test_confidence_bounded_below(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            InterestingEvent(
                detector_name="d",
                vehicle_id="v",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                category="fuel_drop",
                severity="low",
                summary="x",
                confidence=-0.1,
            )

    def test_severity_literal_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            InterestingEvent(
                detector_name="d",
                vehicle_id="v",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                category="fuel_drop",
                severity="catastrophic",  # type: ignore[arg-type]
                summary="x",
                confidence=0.5,
            )

    def test_frozen(self) -> None:
        event = InterestingEvent(
            detector_name="d",
            vehicle_id="v",
            timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
            category="fuel_drop",
            severity="low",
            summary="x",
            confidence=0.5,
        )
        with pytest.raises(ValidationError):
            event.severity = "high"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            InterestingEvent(
                detector_name="d",
                vehicle_id="v",
                timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
                category="fuel_drop",
                severity="low",
                summary="x",
                confidence=0.5,
                priority="urgent",  # type: ignore[call-arg]
            )
