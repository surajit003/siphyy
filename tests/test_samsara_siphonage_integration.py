"""The load-bearing cross-provider test.

Pipes Samsara stats data through ``SamsaraStatsAdapter`` → unmodified
``FuelSiphonageDetector`` and asserts a ``fuel_drop`` event fires on the
planted overnight siphonage scenario.

If this test goes red, the canonical schema's promise — that the same
Tier 1 detector works against any provider's data, after the adapter
boundary — is broken. That's a much bigger deal than the test failing
in isolation.

The detector is instantiated with ``max_minutes=180`` because the
siphonage event in the fixture spans 22:45 → 01:30 (165 minutes) — well
outside the default 60-minute window. This is a configuration choice,
not a detector modification; the detector code itself is unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime

from siphyy.adapters import SamsaraStatsAdapter
from siphyy.detectors import FuelSiphonageDetector
from siphyy.schema import InterestingEvent


def test_samsara_overnight_siphonage_detected(samsara_stats_payload: dict) -> None:
    adapter = SamsaraStatsAdapter()
    # Wider time window to bridge the overnight gap between fuel pings.
    detector = FuelSiphonageDetector(max_minutes=180)

    interesting: list[InterestingEvent] = []
    for event in adapter.adapt(samsara_stats_payload):
        result = detector.process(event)
        if result is not None:
            interesting.append(result)

    # ── Architectural assertion ──────────────────────────────────────
    # At least one fuel_drop event must fire for the planted vehicle.
    fuel_drops = [
        ie
        for ie in interesting
        if ie.category == "fuel_drop" and ie.vehicle_id == "samsara:281474977345001"
    ]
    assert len(fuel_drops) >= 1, (
        "The canonical schema promise is broken: FuelSiphonageDetector "
        "did not fire on a Samsara overnight siphonage event. Either the "
        "adapter isn't emitting readings the detector understands, or the "
        "schema mapping is wrong."
    )

    # ── Locate the overnight firing specifically ─────────────────────
    # The detector fires twice on this fixture:
    #   1. 17:20 — 32% → 22% drop during the day's drive, severity=high.
    #      Technically a Tier 1 false positive (drop is normal consumption,
    #      but the firing reading is at-rest so the rule matches). A real
    #      deployment would let Tier 2 rule this out using a consumption-rate
    #      seed case.
    #   2. 01:30 — 21.5% → 10% overnight drop, severity=critical. The
    #      siphonage scenario the fixture planted.
    overnight = next(
        (ie for ie in fuel_drops if ie.timestamp == datetime(2026, 4, 30, 1, 30, tzinfo=UTC)),
        None,
    )
    assert overnight is not None, (
        f"Expected an overnight (01:30) fuel_drop firing; got firings at "
        f"{[ie.timestamp.isoformat() for ie in fuel_drops]} instead."
    )

    # ── Sanity checks on the overnight event's payload ───────────────
    assert overnight.detector_name == "fuel_siphonage"
    # Drop is ~54% relative — well into the "critical" band (>=40%).
    assert overnight.severity == "critical"
    # Evidence should capture the drop magnitudes (raw matches percent
    # because the adapter mirrors them — see PR notes on schema friction).
    assert overnight.evidence["prior_fuel_level_raw"] == 21.5
    assert overnight.evidence["current_fuel_level_raw"] == 10.0
    assert overnight.evidence["engine_state"] == "stopped"
    assert overnight.evidence["ignition_on"] is False
