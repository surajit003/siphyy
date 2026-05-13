"""Tier 1 fuel siphonage detector.

Fires on the pattern in ``seed_cases.fuel_theft_0001``: a noticeable fuel
level drop while the vehicle is at rest with ignition off. Uses relative
drop in ``fuel_level_raw`` so it works against uncalibrated BLE sensors
as well as calibrated providers — most fuel level sensors are
approximately linear in fuel volume, so relative drop in the raw signal
tracks relative drop in fuel.

This is Tier 1, so the goal is *recall*. Tier 2 (the LLM agent) is the
layer that distinguishes actual siphonage from benign causes like
thermal contraction, sensor drift, or refuel reversals. Don't try to
filter those here.
"""

from __future__ import annotations

from datetime import datetime

from siphyy.detectors.base import Detector, StateStore
from siphyy.schema import CanonicalEvent, InterestingEvent, Severity, TelemetryReading


class FuelSiphonageDetector(Detector):
    """Fuel-drop-while-at-rest detector.

    Parameters:
        state_store: Per-vehicle state. Defaults to an in-memory store.
        threshold_pct: Minimum relative drop to fire. 0.15 = 15%.
        max_minutes: Drops between readings more than this far apart are
            ignored (we can't reliably attribute fuel change to siphonage
            once normal consumption could explain it).
    """

    name = "fuel_siphonage"

    def __init__(
        self,
        state_store: StateStore | None = None,
        threshold_pct: float = 0.15,
        max_minutes: int = 60,
    ) -> None:
        super().__init__(state_store)
        self.threshold_pct = threshold_pct
        self.max_minutes = max_minutes

    def process(self, event: CanonicalEvent) -> InterestingEvent | None:
        if not isinstance(event, TelemetryReading):
            return None
        if event.fuel_level_raw is None:
            return None

        key = self._state_key(event.vehicle_id)
        prior = self.state.get(key)

        # Always record the latest reading so the next call has a baseline.
        self.state.set(
            key,
            {
                "fuel_level_raw": event.fuel_level_raw,
                "timestamp": event.timestamp.isoformat(),
            },
        )

        if prior is None:
            return None  # no baseline yet

        # Rule conditions: vehicle at rest with ignition off.
        if event.ignition_on:
            return None
        if event.engine_state not in ("stopped", "idle"):
            return None

        prior_raw = prior.get("fuel_level_raw")
        if not isinstance(prior_raw, int | float) or prior_raw <= 0:
            return None

        prior_iso = prior.get("timestamp")
        if not isinstance(prior_iso, str):
            return None
        try:
            prior_dt = datetime.fromisoformat(prior_iso)
        except ValueError:
            return None

        elapsed_minutes = (event.timestamp - prior_dt).total_seconds() / 60
        if elapsed_minutes < 0 or elapsed_minutes > self.max_minutes:
            return None

        drop = prior_raw - event.fuel_level_raw
        if drop <= 0:
            return None

        drop_pct = drop / prior_raw
        if drop_pct < self.threshold_pct:
            return None

        return InterestingEvent(
            detector_name=self.name,
            vehicle_id=event.vehicle_id,
            timestamp=event.timestamp,
            category="fuel_drop",
            severity=self._severity_for(drop_pct),
            summary=(
                f"Fuel sensor reading dropped {drop_pct:.0%} over "
                f"{elapsed_minutes:.0f} min while engine_state was "
                f"{event.engine_state} with ignition off."
            ),
            confidence=0.6,
            evidence={
                "drop_pct": round(drop_pct, 4),
                "prior_fuel_level_raw": prior_raw,
                "current_fuel_level_raw": event.fuel_level_raw,
                "elapsed_minutes": round(elapsed_minutes, 1),
                "engine_state": event.engine_state,
                "ignition_on": event.ignition_on,
                "fuel_sensor_type": event.fuel_sensor_type,
            },
            triggering_event_id=event.provider_event_id,
        )

    @staticmethod
    def _severity_for(drop_pct: float) -> Severity:
        if drop_pct >= 0.40:
            return "critical"
        if drop_pct >= 0.25:
            return "high"
        return "medium"
