"""Canonical telematics event schema.

This is the framework contract. Adapters translate provider-specific shapes
into these types. Detectors, agents, and storage all reason in these types.

Schema is versioned via `schema_version`. Breaking changes bump the major
version; new optional fields are non-breaking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

EngineState = Literal["running", "idle", "stopped"]
"""Vehicle motion state. Provider-independent."""

FuelSensorType = Literal["ble", "capacitive", "ultrasonic", "oem_can", "calculated"]
"""Fuel level sensor provenance. Detectors use this to pick noise thresholds —
BLE add-on sensors are noisier than OEM CAN readings, for example."""

DriverEventSubtype = Literal[
    "harsh_brake",
    "harsh_accel",
    "sharp_turn",
    "speeding",
    "idling_start",
    "idling_stop",
    "ignition_on",
    "ignition_off",
]
"""Discrete driver-attributable events. Add cautiously — adding a value here
is a schema change that all adapters and detectors must handle."""


class BaseEvent(BaseModel):
    """Common fields on every canonical event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    vehicle_id: str = Field(
        description="Canonical vehicle identifier. NOT the provider's raw vehicle ID — "
        "adapters are expected to map provider IDs to canonical IDs."
    )
    timestamp: datetime = Field(
        description="Event time in UTC. Adapters convert from local time at the boundary."
    )
    provider: str = Field(description="Name of the adapter that produced this event.")
    provider_event_id: str | None = Field(
        default=None,
        description="Provider's native event ID, used for deduplication. "
        "If the provider doesn't supply one, adapters can synthesize a stable ID.",
    )
    provider_extras: dict[str, object] = Field(
        default_factory=dict,
        description="Provider-specific fields that don't fit the canonical schema. "
        "Preserved for traceability; never used by detectors or agents.",
    )


class TelemetryReading(BaseEvent):
    """A snapshot of vehicle state at a point in time.

    Most fields are optional because not every provider exposes every signal.
    Adapters MUST NOT fabricate values — missing data stays None.
    """

    event_type: Literal["telemetry"] = "telemetry"

    # Position
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None

    # Motion
    speed_kmh: float | None = Field(default=None, ge=0, description="Always in km/h.")
    heading_deg: int | None = Field(default=None, ge=0, lt=360)
    odometer_km: float | None = Field(default=None, ge=0, description="Always in km.")

    # Electrical
    external_voltage_v: float | None = Field(default=None, ge=0)
    battery_percent: float | None = Field(default=None, ge=0, le=100)

    # State
    ignition_on: bool | None = None
    engine_state: EngineState | None = None

    # Fuel — primary input for siphonage detectors. Some providers report
    # calibrated percent/liters directly; others (notably aftermarket BLE
    # sensors) report only a raw reading and require per-vehicle calibration
    # to convert. Adapters without calibration MUST leave the calibrated
    # fields None rather than fabricate them.
    fuel_level_percent: float | None = Field(default=None, ge=0, le=100)
    fuel_level_liters: float | None = Field(default=None, ge=0)
    fuel_level_raw: float | None = Field(
        default=None,
        ge=0,
        description="Uncalibrated sensor reading in whatever unit the sensor emits. "
        "Useful when calibration isn't available — relative changes still inform "
        "detectors even when absolute volume isn't known.",
    )
    fuel_sensor_type: FuelSensorType | None = None
    tank_capacity_liters: float | None = Field(
        default=None,
        gt=0,
        description="Vehicle metadata, when known. Needed by detectors that reason in "
        "absolute volumes — e.g. thermal-contraction expected drop ≈ "
        "capacity * 0.0008 * dT_celsius for diesel.",
    )

    # Environment
    ambient_temperature_c: float | None = Field(
        default=None,
        description="Ambient air temperature at the vehicle, if the provider supplies "
        "it or a weather join is performed upstream. Required to rule out "
        "thermal contraction on overnight fuel-level drops.",
    )

    # Orientation — provider-dependent. Some telematics devices expose
    # accelerometer-derived attitude (Teltonika FMx via AVL IDs 256/257,
    # Queclink GLx, OEM CAN); cheaper trackers don't. Leave as None when
    # the provider has no signal — never approximate from altitude or
    # GPS heading.
    pitch_deg: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description=(
            "Vehicle pitch (front-to-back tilt) in degrees, signed; positive = "
            "nose up. "
            "WHY THIS MATTERS FOR FUEL SIPHONAGE: fuel level sensors sit at a "
            "fixed point inside a horizontal tank. When the truck pitches, fuel "
            "pools at one end and the reading shifts even though no fuel left "
            "the tank. A 10° pitch on a 1000 L tank can show ~20% apparent "
            "change — enough to clear most Tier 1 thresholds. Without pitch "
            "context, 'parked on a slope' and 'just finished a climb' "
            "masquerade as siphonage."
        ),
    )
    roll_deg: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description=(
            "Vehicle roll (side-to-side tilt) in degrees, signed; positive = "
            "right side up. Less load-bearing than pitch for siphonage on "
            "longitudinal tanks, but matters for saddle tanks and tanker "
            "compartments with side-mounted probes."
        ),
    )

    # Geocoded labels — preserved when provider supplies them
    location_text: str | None = Field(
        default=None,
        description="Reverse-geocoded address if the provider supplies it. "
        "Saves a separate geocoding API call for the LLM agent.",
    )
    poi_text: str | None = Field(
        default=None,
        description="Nearest point-of-interest description, e.g. '0.3 km from Pepsi Main Plant'.",
    )


class DriverEvent(BaseEvent):
    """A discrete driver-attributable event.

    These are typically server-computed by the provider (e.g. Samsara fires
    harsh braking events). When the provider only exposes raw accelerometer
    data, the adapter — not Tier 1 — is responsible for synthesizing these.
    """

    event_type: Literal["driver_event"] = "driver_event"

    subtype: DriverEventSubtype
    severity: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Provider-reported severity if available, normalized to 0-1.",
    )
    g_force: float | None = Field(
        default=None,
        ge=0,
        description="Peak g-force for harsh-event subtypes.",
    )
    duration_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Duration for sustained events like speeding or idling.",
    )

    # Position context
    latitude: float | None = None
    longitude: float | None = None


CanonicalEvent = Annotated[
    TelemetryReading | DriverEvent,
    Field(discriminator="event_type"),
]
"""Discriminated union over all canonical event types.

Detectors and storage code should annotate against `CanonicalEvent`, not the
individual types, so that adding new event types doesn't require touching them.
"""
