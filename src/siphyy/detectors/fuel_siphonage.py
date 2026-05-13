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

        # Cache the orientation/altitude context too so the next call can
        # tell whether the vehicle just climbed a grade or was tilted.
        # Tier 1 doesn't act on this directly; it lands in evidence so the
        # agent can reason about slope-effect false positives (see the
        # `slope_effect` seed case).
        current_state: dict[str, object] = {
            "fuel_level_raw": event.fuel_level_raw,
            "timestamp": event.timestamp.isoformat(),
        }
        if event.altitude_m is not None:
            current_state["altitude_m"] = event.altitude_m
        if event.pitch_deg is not None:
            current_state["pitch_deg"] = event.pitch_deg
        self.state.set(key, current_state)

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

        evidence: dict[str, object] = {
            "drop_pct": round(drop_pct, 4),
            "prior_fuel_level_raw": prior_raw,
            "current_fuel_level_raw": event.fuel_level_raw,
            "elapsed_minutes": round(elapsed_minutes, 1),
            "engine_state": event.engine_state,
            "ignition_on": event.ignition_on,
            "fuel_sensor_type": event.fuel_sensor_type,
        }
        self._add_orientation_evidence(evidence, event, prior)

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
            evidence=evidence,
            triggering_event_id=event.provider_event_id,
        )

    @staticmethod
    def _add_orientation_evidence(
        evidence: dict[str, object],
        event: TelemetryReading,
        prior: dict[str, object],
    ) -> None:
        """Attach altitude and pitch context so the agent can rule out
        slope-effect false positives. Only adds fields that are actually
        known — never None — so the agent doesn't have to filter them."""
        if event.altitude_m is not None:
            evidence["current_altitude_m"] = event.altitude_m
        prior_alt = prior.get("altitude_m")
        if isinstance(prior_alt, int | float):
            evidence["prior_altitude_m"] = prior_alt
            if event.altitude_m is not None:
                evidence["altitude_delta_m"] = round(event.altitude_m - prior_alt, 1)

        if event.pitch_deg is not None:
            evidence["current_pitch_deg"] = event.pitch_deg
        prior_pitch = prior.get("pitch_deg")
        if isinstance(prior_pitch, int | float):
            evidence["prior_pitch_deg"] = prior_pitch

        if event.roll_deg is not None:
            evidence["current_roll_deg"] = event.roll_deg

    @staticmethod
    def _severity_for(drop_pct: float) -> Severity:
        if drop_pct >= 0.40:
            return "critical"
        if drop_pct >= 0.25:
            return "high"
        return "medium"
