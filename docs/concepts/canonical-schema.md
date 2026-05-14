# Canonical schema

The canonical schema is the framework's load-bearing contract. Everything past the adapter layer reasons in these types, never in raw provider dicts. Detectors, agents, storage code, and your own downstream business logic all import from `siphyy.schema` and ignore the wire format the data arrived in.

## The shape

Three top-level types, two of them events:

- **`TelemetryReading`** — point-in-time snapshot of a vehicle (position, motion, fuel, orientation, electrical state). The bulk of any provider's data.
- **`DriverEvent`** — discrete driver-attributable events (harsh brake, speeding, idling). Smaller volume, more semantic.
- **`InterestingEvent`** — emitted by Tier 1 detectors, consumed by Tier 2 agents.

All three are frozen Pydantic models with `extra="forbid"` — typos and provider drift become loud `ValidationError`s, not silent data corruption.

## Five rules every field obeys

1. **Units are canonical.** Kilometres, kilometres-per-hour, Celsius, UTC. Adapters convert at the boundary. Downstream code never has to think about miles, mph, Fahrenheit, or local time.
2. **Missing data is `None`, never fabricated.** If a provider doesn't expose RPM, the field is `None`. Detectors handle `None` gracefully. The framework's rule is: *we do not lie to ourselves*.
3. **Bounds are enforced where physical bounds exist.** `speed_kmh >= 0`. `battery_percent` in `[0, 100]`. `fuel_level_percent` in `[0, 100]`. Out-of-range values raise at construction time.
4. **No provider-specific fields in the canonical type.** Whatever doesn't fit goes into `provider_extras: dict`. *Detectors and agents do not read `provider_extras`* — that's the explicit rule the framework lives by.
5. **Field descriptions explain the *why*, not just the *what*.** Read [`canonical.py`](https://github.com/surajit003/siphyy/blob/main/src/siphyy/schema/canonical.py) — most descriptions explain when the field matters and why a detector needs it. This is the load-bearing documentation; it's where the framework's reasoning lives.

## Why fuel is first-class (and what it teaches)

The framework's biggest schema decision was promoting fuel data out of `provider_extras` into first-class fields on `TelemetryReading`:

- `fuel_level_percent`, `fuel_level_liters`, `fuel_level_raw`, `fuel_sensor_type`, `tank_capacity_liters`, `ambient_temperature_c`, `pitch_deg`, `roll_deg`.

Why? Because the planned siphonage detector would have had to read `provider_extras["auxiliary_channels"]` to get the BLE fuel sensor's value. Doing so would violate the framework's own canonical-contract rule. The fix was to ask "does fuel deserve to be canonical?" — and the answer was obviously yes, since fuel is the framework's primary subject matter.

**The pattern this encodes for future fields:** if you find a detector reaching into `provider_extras` for something, that's a signal the schema needs a new field, not that the detector is fine. Same shape for: tank capacity (added when slope-effect cases needed it), pitch/roll (added when the slope-effect false-positive seed case appeared).

## Discriminated union

`CanonicalEvent` is a discriminated union over `TelemetryReading | DriverEvent`, discriminated on the `event_type` field. JSON round-trips through Pydantic preserve type — the discriminator survives serialisation.

```python
from siphyy.schema import CanonicalEvent
# A function declaring CanonicalEvent accepts either subtype:
def store(event: CanonicalEvent) -> None:
    ...
```

Adding a new event type (`MaintenanceEvent` is one we'd consider) is a schema-version bump — all adapters and detectors get to opt in deliberately.

## Provider-specific data lives in `provider_extras`

When a provider has fields that don't fit canonically, the adapter stashes them in `provider_extras: dict[str, object]` — preserved for traceability, never used by Tier 1 or Tier 2 logic. That's the architectural commitment.

Examples from `TrakzeeAdapter`:

- `provider_extras["auxiliary_channels"]` — the raw BLE sensor list, kept around so multi-sensor trucks aren't lossy (canonical only carries the primary BLE reading).
- `provider_extras["company"]`, `provider_extras["branch"]` — operational metadata that some users will care about but the framework's detectors don't.

If you're tempted to read `provider_extras` from a detector or agent: stop, and consider whether the canonical schema needs a new field instead.

## Version

`schema_version: Literal["1.0"]` is on every event. Bumping the major version is a breaking change everyone has to acknowledge; adding new *optional* fields is non-breaking. Renaming an existing field, narrowing its type, or removing it is breaking.
