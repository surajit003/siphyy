# Writing an adapter for a new telematics provider

The whole point of the canonical schema is that you don't have to wait for us to support your provider. If you can read your provider's data, you can write an adapter in 30–60 minutes.

## The contract

Subclass `TelematicsAdapter` and implement one method:

```python
from collections.abc import Iterable
from siphyy.adapters.base import TelematicsAdapter
from siphyy.schema import CanonicalEvent

class MyProviderAdapter(TelematicsAdapter):
    name = "myprovider"  # appears as `provider` on emitted events

    def adapt(self, raw: Iterable[object]) -> Iterable[CanonicalEvent]:
        for record in raw:
            # ...translate `record` into TelemetryReading / DriverEvent instances
            yield event
```

That's the whole API surface. Everything else is internal to your adapter.

## The five rules

1. **Convert units at the boundary.** Canonical schema uses km, km/h, Celsius, and UTC. If your provider gives mph, miles, Fahrenheit, or local time, convert inside your adapter. Downstream code should never see provider units.

2. **Missing data stays `None`.** If your provider doesn't expose RPM, set `rpm=None`. Never fabricate a "reasonable default" — detectors and agents are designed to handle missing data correctly. Faking it poisons their reasoning.

3. **Preserve provider-specific fields in `provider_extras`.** Anything that doesn't fit the canonical schema but might be useful — go in `provider_extras: dict`. Don't lose data; don't pollute the contract.

4. **Map vehicle IDs to canonical IDs.** Your provider has its own vehicle identifier. Either expose a `vehicle_id_mapping` parameter (like `TrakzeeAdapter`) or use a stable, prefixed default like `"yourprovider:{provider_id}"`. Never emit raw provider IDs as canonical — fleets often have the same physical vehicle in multiple systems.

5. **Stay pure.** No network calls inside the adapter. No DB writes. No shared mutable state. Adapters should be safe to call from multiple threads.

## Reference: TrakzeeAdapter

The Trakzee adapter is the reference implementation. Read `src/siphyy/adapters/trakzee.py` end-to-end before writing your own — it demonstrates every pattern you'll need:

- Unit conversion (meters → km on odometer)
- Timezone conversion (local time → UTC)
- Status enum mapping (`"RUNNING"` → `"running"`)
- Optional auxiliary data parsing (BLE fuel JSON)
- Graceful handling of `--` / `NA` / `nan` placeholders

## Testing

Mirror `tests/test_trakzee_adapter.py` for your provider:

1. Add a realistic sample row as a pytest fixture in `conftest.py`.
2. Write tests for: valid row → expected canonical event, missing data → `None` fields, edge cases specific to your provider.
3. Aim for 90%+ coverage on the adapter — adapters are the most failure-prone part of the framework because real data is always messier than docs suggest.

## Running the validator

Before opening a PR:

```bash
pytest tests/test_yourprovider_adapter.py -v
ruff check src/siphyy/adapters/yourprovider.py
mypy src/siphyy/adapters/yourprovider.py
```

All three must pass.

## One pattern that comes up

If your provider has both a "positions" endpoint (continuous telemetry) and an "events" endpoint (discrete driver events), write **two adapter classes** rather than one mega-adapter. Single Responsibility wins:

```python
class MyProviderPositionsAdapter(TelematicsAdapter):
    name = "myprovider"

    def adapt(self, raw):  # emits TelemetryReading
        ...

class MyProviderEventsAdapter(TelematicsAdapter):
    name = "myprovider"

    def adapt(self, raw):  # emits DriverEvent
        ...
```

They share `name` because they're the same logical provider; they're separate classes because they consume different shapes of input.
