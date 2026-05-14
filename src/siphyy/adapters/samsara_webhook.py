"""Adapter for Samsara push-based webhook alerts.

Samsara webhooks come in many flavours; this adapter handles the
subset relevant to canonical ``DriverEvent`` emission today:

* ``eventType=HarshEvent`` with ``harshEventType in {HarshBraking,
  HarshAcceleration}`` → corresponding ``harsh_brake``/``harsh_accel``
  driver event.
* ``eventType=Alert`` with ``alertConditionId=DeviceSpeedAbove`` →
  ``speeding`` driver event.
* ``eventType=Alert`` with ``alertConditionId=DeviceLocationOutsideGeofence``
  → silently skipped. The canonical schema has no ``geofence_exit``
  event subtype yet; rather than fabricate one, we drop the payload
  on the floor. Adding a geofence event type to the schema is a
  separate, deliberate change.
* Anything else (sharp-turn alerts, login alerts, fuel-card alerts,
  ...) → silently skipped. Add new branches here as the canonical
  schema grows new ``DriverEventSubtype`` values.

Same provider name as ``SamsaraStatsAdapter`` — both classes adapt the
same underlying telematics provider, just different payload shapes.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from siphyy.adapters.base import TelematicsAdapter
from siphyy.schema import CanonicalEvent, DriverEvent, DriverEventSubtype

_MPH_TO_KMH = 1.609344


class SamsaraWebhookAdapter(TelematicsAdapter):
    """Translates Samsara webhook payloads into canonical ``DriverEvent``s."""

    name = "samsara"
    schema_version = "1.0"

    def __init__(self, vehicle_id_mapping: dict[str, str] | None = None) -> None:
        self.vehicle_id_mapping = vehicle_id_mapping or {}

    def adapt(self, raw: Iterable[object]) -> Iterable[CanonicalEvent]:
        for webhook in raw:
            if not isinstance(webhook, dict):
                continue
            event = self._adapt_webhook(webhook)
            if event is not None:
                yield event

    # ── internals ────────────────────────────────────────────────────

    def _adapt_webhook(self, webhook: dict[str, Any]) -> DriverEvent | None:
        event_type = webhook.get("eventType")
        data = webhook.get("data")
        if not isinstance(data, dict):
            return None

        if event_type == "HarshEvent":
            return self._adapt_harsh_event(webhook, data)

        if event_type == "Alert":
            return self._adapt_alert(webhook, data)

        # Unknown / not-yet-handled event types: silently skipped.
        return None

    def _adapt_harsh_event(
        self, webhook: dict[str, Any], data: dict[str, Any]
    ) -> DriverEvent | None:
        harsh_type = data.get("harshEventType")
        subtype: DriverEventSubtype | None
        if harsh_type == "HarshBraking":
            subtype = "harsh_brake"
        elif harsh_type == "HarshAcceleration":
            subtype = "harsh_accel"
        else:
            return None
        return self._build_driver_event(webhook, data, subtype)

    def _adapt_alert(self, webhook: dict[str, Any], data: dict[str, Any]) -> DriverEvent | None:
        condition = data.get("alertConditionId")
        if condition == "DeviceSpeedAbove":
            return self._build_driver_event(webhook, data, "speeding")
        # Geofence + everything else: skip silently. Adding handlers here
        # requires the canonical schema to grow matching DriverEventSubtype
        # values.
        return None

    def _build_driver_event(
        self,
        webhook: dict[str, Any],
        data: dict[str, Any],
        subtype: DriverEventSubtype,
    ) -> DriverEvent | None:
        vehicle = data.get("vehicle") or {}
        vehicle_id_raw = str(vehicle.get("id", "")).strip()
        if not vehicle_id_raw:
            return None
        vehicle_id = self.vehicle_id_mapping.get(vehicle_id_raw, f"samsara:{vehicle_id_raw}")

        timestamp = self._parse_iso(webhook.get("eventTime"))
        if timestamp is None:
            return None

        location = data.get("location") or {}
        latitude = self._safe_float(location.get("latitude"))
        longitude = self._safe_float(location.get("longitude"))

        provider_extras = self._build_extras(webhook, data, subtype)

        return DriverEvent(
            vehicle_id=vehicle_id,
            timestamp=timestamp,
            provider=self.name,
            provider_event_id=self._safe_str(webhook.get("eventId")),
            subtype=subtype,
            latitude=latitude,
            longitude=longitude,
            # Samsara webhooks don't expose g-force per incident; the
            # canonical field stays None for speeding by spec and for
            # harsh-events because the data isn't reliably in the payload.
            g_force=None,
            provider_extras=provider_extras,
        )

    @staticmethod
    def _build_extras(
        webhook: dict[str, Any], data: dict[str, Any], subtype: DriverEventSubtype
    ) -> dict[str, object]:
        """Preserve event-specific Samsara fields so downstream UI can
        surface them, without polluting the canonical event schema."""
        extras: dict[str, object] = {}
        for top_key in ("orgId", "webhookId"):
            if webhook.get(top_key) not in (None, ""):
                extras[top_key] = webhook[top_key]
        for data_key in ("driver", "details", "alertConditionDescription"):
            val = data.get(data_key)
            if val not in (None, ""):
                extras[data_key] = val
        # Speed at the moment of the incident (mph) — preserve the original
        # value, plus the canonical km/h conversion for downstream tools.
        speed_mph = data.get(
            "speedMilesPerHour" if subtype == "speeding" else "speedAtTimeOfIncidentMilesPerHour"
        )
        if isinstance(speed_mph, int | float) and not isinstance(speed_mph, bool):
            extras["speed_mph"] = float(speed_mph)
            extras["speed_kmh"] = float(speed_mph) * _MPH_TO_KMH
        speed_limit_mph = data.get("speedLimitMilesPerHour")
        if isinstance(speed_limit_mph, int | float) and not isinstance(speed_limit_mph, bool):
            extras["speed_limit_mph"] = float(speed_limit_mph)
            extras["speed_limit_kmh"] = float(speed_limit_mph) * _MPH_TO_KMH
        return extras

    @staticmethod
    def _parse_iso(raw: object) -> datetime | None:
        if not isinstance(raw, str) or not raw:
            return None
        try:
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
    def _safe_str(raw: object) -> str | None:
        if not isinstance(raw, str):
            return None
        s = raw.strip()
        return s or None
