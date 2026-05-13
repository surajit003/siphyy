"""Adapter for Trakzee positions exports.

Trakzee is a polling-based provider: rows are point-in-time snapshots of
vehicle state, fetched every few minutes. Each row becomes one
TelemetryReading. State transitions (e.g. RUNNING -> STOP) are detected
downstream in Tier 1, NOT in the adapter.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from siphyy.adapters.base import TelematicsAdapter
from siphyy.schema import CanonicalEvent, EngineState, FuelSensorType, TelemetryReading

# Trakzee export timestamps are in the fleet operator's local time, not UTC.
# Default here is Lusaka (CAT, UTC+2) since the reference data is from a
# Zambian fleet. Callers SHOULD pass `source_timezone` explicitly.
LUSAKA_TZ = timezone(timedelta(hours=2))


_STATUS_TO_ENGINE_STATE: dict[str, EngineState] = {
    "RUNNING": "running",
    "IDLE": "idle",
    "STOP": "stopped",
}

_MISSING_VALUES = frozenset({"--", "NA", "nan", ""})


class TrakzeeAdapter(TelematicsAdapter):
    """Translates Trakzee positions/telemetry exports into canonical events."""

    name = "trakzee"
    schema_version = "1.0"

    def __init__(
        self,
        vehicle_id_mapping: dict[str, str] | None = None,
        source_timezone: timezone = LUSAKA_TZ,
    ) -> None:
        # In production: lookup table mapping Trakzee IMEI -> canonical vehicle UUID.
        self.vehicle_id_mapping = vehicle_id_mapping or {}
        self.source_tz = source_timezone

    def adapt(self, raw: Iterable[object]) -> Iterable[CanonicalEvent]:
        for row in raw:
            if not isinstance(row, dict):
                continue
            event = self._adapt_row(row)
            if event is not None:
                yield event

    # ---- internals -------------------------------------------------

    def _adapt_row(self, row: dict[str, Any]) -> TelemetryReading | None:
        imei = str(row.get("Imeino", "")).strip()
        if not imei or imei == "nan":
            return None

        vehicle_id = self.vehicle_id_mapping.get(imei, f"trakzee:{imei}")

        timestamp = self._parse_local_datetime(row.get("GPSActualTime"))
        if timestamp is None:
            return None

        engine_state = _STATUS_TO_ENGINE_STATE.get(str(row.get("Status", "")).strip().upper())
        ignition_on = str(row.get("IGN", "")).strip().upper() == "ON"

        # Numeric fields with safe coercion
        speed_kmh = self._safe_float(row.get("Speed"))
        heading_deg = self._safe_int(row.get("Angle"))
        latitude = self._safe_float(row.get("Latitude"))
        longitude = self._safe_float(row.get("Longitude"))
        altitude_m = self._safe_float(row.get("Altitude"))
        external_voltage_v = self._safe_float(row.get("ExternalVolt"))
        battery_percent = self._safe_float(row.get("battery_percentage"))

        # Trakzee reports odometer in meters; canonical schema is km.
        odo_raw = self._safe_float(row.get("Odometer"))
        odometer_km = odo_raw / 1000.0 if odo_raw is not None else None

        location_text = self._clean_text(row.get("Location"))
        poi_text = self._clean_text(row.get("POI"))

        # Auxiliary channels JSON (BLE fuel sensors) lives in `Fuel`, not `AC`,
        # despite the misleading column name. Caught this only by testing the
        # adapter against real exports.
        provider_extras: dict[str, object] = {}
        fuel_aux = self._parse_aux_json(row.get("Fuel"))
        fuel_level_raw: float | None = None
        fuel_sensor_type: FuelSensorType | None = None
        if fuel_aux:
            provider_extras["auxiliary_channels"] = fuel_aux
            primary_ble = self._primary_ble_fuel(fuel_aux)
            if primary_ble is not None:
                # Trakzee exposes BLE readings as raw sensor counts, not
                # calibrated percent or volume. Per-vehicle calibration lives
                # outside the adapter, so percent/liters stay None.
                fuel_level_raw = primary_ble
                fuel_sensor_type = "ble"

        ac_text = self._clean_text(row.get("AC"))
        if ac_text:
            provider_extras["ac_raw"] = ac_text

        # Orientation (pitch/roll) is not present in the default Trakzee
        # positions export. The underlying Teltonika FMB920 firmware does
        # expose it via AVL IDs 256 (Axis X / pitch) and 257 (Axis Y / roll);
        # operators can enable those channels in the Trakzee data profile
        # and they will arrive as additional columns. When that happens,
        # promote them into canonical pitch_deg / roll_deg (in degrees,
        # signed) here — see canonical.py for why these fields matter to
        # the FuelSiphonageDetector.

        # Preserve provider-specific identifiers/metadata for traceability.
        for key in (
            "Vehicle_No",
            "Vehicle_Name",
            "Company",
            "Branch",
            "Vehicletype",
            "DeviceModel",
        ):
            val = row.get(key)
            if val is not None and str(val).strip() not in _MISSING_VALUES:
                provider_extras[key.lower()] = val

        return TelemetryReading(
            vehicle_id=vehicle_id,
            timestamp=timestamp,
            provider=self.name,
            provider_event_id=f"{imei}:{int(timestamp.timestamp())}",
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude_m,
            speed_kmh=speed_kmh,
            heading_deg=heading_deg,
            odometer_km=odometer_km,
            external_voltage_v=external_voltage_v,
            battery_percent=battery_percent,
            ignition_on=ignition_on,
            engine_state=engine_state,
            fuel_level_raw=fuel_level_raw,
            fuel_sensor_type=fuel_sensor_type,
            location_text=location_text,
            poi_text=poi_text,
            provider_extras=provider_extras,
        )

    def _parse_local_datetime(self, raw: object) -> datetime | None:
        """Parse 'DD-MM-YYYY HH:MM:SS' (in source_tz) and return UTC datetime."""
        if raw is None:
            return None
        s = str(raw).strip()
        if s in _MISSING_VALUES:
            return None
        try:
            local = datetime.strptime(s, "%d-%m-%Y %H:%M:%S")
            return local.replace(tzinfo=self.source_tz).astimezone(UTC)
        except ValueError, TypeError:
            return None

    def _primary_ble_fuel(self, aux: list[dict[str, Any]]) -> float | None:
        """First BLE Fuel Level sensor's raw value, or None if absent.

        Multi-sensor trucks (main + reserve tanks) report multiple BLE
        channels; promoting only the first keeps the canonical record
        single-valued. Callers needing every sensor read
        ``provider_extras["auxiliary_channels"]`` directly.
        """
        for entry in aux:
            if not isinstance(entry, dict):
                continue
            if "BLE Fuel Level" in str(entry.get("port_name", "")):
                return self._safe_float(entry.get("value"))
        return None

    def _parse_aux_json(self, raw: object) -> list[dict[str, Any]] | None:
        if raw is None:
            return None
        s = str(raw).strip()
        if s in _MISSING_VALUES or s == "[]":
            return None
        try:
            parsed = json.loads(s) if isinstance(raw, str) else raw
            return parsed if isinstance(parsed, list) and parsed else None
        except json.JSONDecodeError, TypeError:
            return None

    def _safe_float(self, raw: object) -> float | None:
        if raw is None:
            return None
        s = str(raw).strip()
        if s in _MISSING_VALUES:
            return None
        try:
            f = float(raw)  # type: ignore[arg-type]
            return None if math.isnan(f) else f
        except ValueError, TypeError:
            return None

    def _safe_int(self, raw: object) -> int | None:
        f = self._safe_float(raw)
        return int(f) if f is not None else None

    def _clean_text(self, raw: object) -> str | None:
        if raw is None:
            return None
        s = str(raw).strip()
        return None if s in _MISSING_VALUES else s
