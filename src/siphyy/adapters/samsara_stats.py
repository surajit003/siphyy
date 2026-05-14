"""Adapter for the Samsara stats feed / stats history shape.

Samsara's polled telemetry endpoint groups output by vehicle, with each
signal (GPS, engineStates, fuelPercents, obdOdometerMeters, ...) as a
separate time-indexed array hanging off the vehicle object. This adapter
flattens that into one canonical ``TelemetryReading`` per unique
timestamp seen across any signal for that vehicle:

* Signals that share a timestamp get merged into the same reading.
* ``engineStates`` is event-based and sparse (records transitions only),
  so it's forward-filled — the engine state at any reading is the most
  recent value at-or-before that timestamp.
* Timestamps where only fuel data exists still produce a reading
  (carrying that fuel value + the carried-forward engine state),
  because those are exactly the points the siphonage detector cares
  about.

Samsara webhooks (push-based alerts like HarshBraking) are a different
shape — see ``samsara_webhook.py`` for that adapter. Both classes share
``name = "samsara"`` because they're the same provider.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from siphyy.adapters.base import TelematicsAdapter
from siphyy.schema import CanonicalEvent, EngineState, TelemetryReading

# mph → km/h. 1 mile = 1.609344 km exactly.
_MPH_TO_KMH = 1.609344


class SamsaraStatsAdapter(TelematicsAdapter):
    """Translates Samsara ``stats/feed`` / ``stats/history`` payloads into
    canonical ``TelemetryReading``s.

    The expected input is the full dict returned by either endpoint —
    ``{"data": [{"id": "...", "gps": [...], "engineStates": [...], ...}],
    "pagination": {...}}``.
    """

    name = "samsara"
    schema_version = "1.0"

    def __init__(self, vehicle_id_mapping: dict[str, str] | None = None) -> None:
        # Production: lookup table mapping Samsara device id → canonical UUID.
        self.vehicle_id_mapping = vehicle_id_mapping or {}

    def adapt(self, raw: Iterable[object]) -> Iterable[CanonicalEvent]:
        # Samsara responses are a single dict, not an iterable of rows — but
        # we accept both shapes so the same adapter can be fed paginated
        # results one page at a time, or a single response.
        if isinstance(raw, dict):
            yield from self._adapt_response(raw)
            return
        for page in raw:
            if isinstance(page, dict):
                yield from self._adapt_response(page)

    # ── internals ────────────────────────────────────────────────────

    def _adapt_response(self, response: dict[str, Any]) -> Iterable[TelemetryReading]:
        data = response.get("data", [])
        if not isinstance(data, list):
            return
        for vehicle_data in data:
            if isinstance(vehicle_data, dict):
                yield from self._adapt_vehicle(vehicle_data)

    def _adapt_vehicle(self, vehicle_data: dict[str, Any]) -> Iterable[TelemetryReading]:
        vehicle_id_raw = str(vehicle_data.get("id", "")).strip()
        if not vehicle_id_raw:
            return
        vehicle_id = self.vehicle_id_mapping.get(vehicle_id_raw, f"samsara:{vehicle_id_raw}")

        gps_by_time = self._index_by_time(vehicle_data.get("gps", []))
        fuel_by_time = self._index_by_time(vehicle_data.get("fuelPercents", []))
        odo_by_time = self._index_by_time(vehicle_data.get("obdOdometerMeters", []))
        engine_states = self._parse_engine_states(vehicle_data.get("engineStates", []))

        provider_extras_base = self._build_vehicle_extras(vehicle_data)

        all_times = sorted(set(gps_by_time) | set(fuel_by_time) | set(odo_by_time))
        for ts in all_times:
            yield self._build_reading(
                vehicle_id=vehicle_id,
                vehicle_id_raw=vehicle_id_raw,
                ts=ts,
                gps=gps_by_time.get(ts),
                fuel=fuel_by_time.get(ts),
                odo=odo_by_time.get(ts),
                engine_states=engine_states,
                provider_extras_base=provider_extras_base,
            )

    def _build_reading(
        self,
        *,
        vehicle_id: str,
        vehicle_id_raw: str,
        ts: datetime,
        gps: dict[str, Any] | None,
        fuel: dict[str, Any] | None,
        odo: dict[str, Any] | None,
        engine_states: list[tuple[datetime, str]],
        provider_extras_base: dict[str, object],
    ) -> TelemetryReading:
        engine_state, ignition_on = self._engine_state_at(engine_states, ts)

        gps = gps or {}
        fuel = fuel or {}
        odo = odo or {}

        latitude = self._safe_float(gps.get("latitude"))
        longitude = self._safe_float(gps.get("longitude"))
        heading_deg = self._safe_int(gps.get("headingDegrees"))
        speed_mph = self._safe_float(gps.get("speedMilesPerHour"))
        speed_kmh = speed_mph * _MPH_TO_KMH if speed_mph is not None else None

        reverse_geo = gps.get("reverseGeo") or {}
        location_text = self._clean_text(reverse_geo.get("formattedLocation"))

        odo_meters = self._safe_float(odo.get("value"))
        odometer_km = odo_meters / 1000.0 if odo_meters is not None else None

        fuel_pct = self._safe_float(fuel.get("value"))

        return TelemetryReading(
            vehicle_id=vehicle_id,
            timestamp=ts,
            provider=self.name,
            provider_event_id=f"{vehicle_id_raw}:{int(ts.timestamp())}",
            latitude=latitude,
            longitude=longitude,
            heading_deg=heading_deg,
            speed_kmh=speed_kmh,
            odometer_km=odometer_km,
            engine_state=engine_state,
            ignition_on=ignition_on,
            location_text=location_text,
            fuel_level_percent=fuel_pct,
            # The reference detector reads fuel_level_raw to stay neutral
            # about the calibration of the source signal. Samsara already
            # ships a calibrated percent, so the "raw" view is the same
            # number — set both so the canonical schema is honest and the
            # detector still works. See PR notes on schema friction.
            fuel_level_raw=fuel_pct,
            fuel_sensor_type=self._fuel_sensor_type_for(fuel_pct),
            provider_extras=dict(provider_extras_base),
        )

    @staticmethod
    def _fuel_sensor_type_for(fuel_pct: float | None) -> str | None:
        # Samsara doesn't expose the underlying sensor's provenance through
        # this endpoint. If a value came through, the most accurate label
        # is "calculated" (Samsara's fleet platform derives the percent from
        # OEM CAN where available, or from add-on sensors otherwise).
        return "calculated" if fuel_pct is not None else None

    @staticmethod
    def _build_vehicle_extras(vehicle_data: dict[str, Any]) -> dict[str, object]:
        """Carry forward Samsara-specific vehicle metadata onto every event
        emitted for this vehicle. The schema rule (never read provider_extras
        in detectors/agents) means this stays advisory — useful for
        traceability and downstream UI."""
        extras: dict[str, object] = {}
        for key in ("name",):
            val = vehicle_data.get(key)
            if val not in (None, ""):
                extras[key] = val
        external_ids = vehicle_data.get("externalIds")
        if isinstance(external_ids, dict) and external_ids:
            extras["externalIds"] = external_ids
        return extras

    def _index_by_time(self, entries: Any) -> dict[datetime, dict[str, Any]]:
        result: dict[datetime, dict[str, Any]] = {}
        if not isinstance(entries, list):
            return result
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ts = self._parse_iso(entry.get("time"))
            if ts is None:
                continue
            result[ts] = entry
        return result

    def _parse_engine_states(self, entries: Any) -> list[tuple[datetime, str]]:
        out: list[tuple[datetime, str]] = []
        if not isinstance(entries, list):
            return out
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ts = self._parse_iso(entry.get("time"))
            value = entry.get("value")
            if ts is None or not isinstance(value, str):
                continue
            out.append((ts, value))
        out.sort(key=lambda pair: pair[0])
        return out

    def _engine_state_at(
        self,
        engine_states: list[tuple[datetime, str]],
        ts: datetime,
    ) -> tuple[EngineState | None, bool | None]:
        """Forward-fill: pick the most recent state at-or-before ts."""
        latest: str | None = None
        for entry_ts, value in engine_states:
            if entry_ts <= ts:
                latest = value
            else:
                break
        if latest == "On":
            return "running", True
        if latest == "Off":
            return "stopped", False
        return None, None

    @staticmethod
    def _parse_iso(raw: object) -> datetime | None:
        if not isinstance(raw, str) or not raw:
            return None
        try:
            # 3.11+ datetime.fromisoformat handles trailing 'Z'.
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def _safe_float(raw: object) -> float | None:
        if raw is None or isinstance(raw, bool):
            return None
        try:
            f = float(raw)  # type: ignore[arg-type]
            return None if math.isnan(f) else f
        except TypeError, ValueError:
            return None

    @staticmethod
    def _safe_int(raw: object) -> int | None:
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, int | float | str):
            try:
                return int(raw)
            except TypeError, ValueError:
                return None
        return None

    @staticmethod
    def _clean_text(raw: object) -> str | None:
        if not isinstance(raw, str):
            return None
        s = raw.strip()
        return s or None
