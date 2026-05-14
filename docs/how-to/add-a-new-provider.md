# Add a new telematics provider

If your fleet runs on Samsara, Geotab, Verizon Connect, an OEM-specific telematics gateway, or anything else nobody has adapted yet, the path is the same: subclass `TelematicsAdapter`, implement one method, write tests. ~50 lines for most providers.

## The shape

```python
from collections.abc import Iterable
from siphyy.adapters.base import TelematicsAdapter
from siphyy.schema import CanonicalEvent

class MyProviderAdapter(TelematicsAdapter):
    name = "myprovider"   # lowercase, no spaces, appears as `provider` on every event

    def adapt(self, raw: Iterable[object]) -> Iterable[CanonicalEvent]:
        for record in raw:
            # ... translate into TelemetryReading / DriverEvent and yield
            yield event
```

For the full walkthrough including the five rules, unit conversions, missing-data handling, and the `TrakzeeAdapter` worked example, see the [Writing an adapter tutorial](../tutorial/writing-an-adapter.md).

## Provider-specific gotchas worth checking

Real-world telematics exports break in predictable ways. Run through this list when designing your adapter:

- **Timestamp format and timezone.** Many exports use local time without a TZ suffix. Make timezone a constructor parameter, not a hardcoded default. Convert to UTC at the boundary.
- **Units.** Odometer in metres vs km vs miles. Speed in m/s vs km/h vs mph. Fuel in litres, gallons, or raw sensor counts. Convert at the boundary.
- **Vehicle ID stability.** Some providers' "vehicle ID" changes when the operator re-pairs the device. Use the IMEI/serial as the stable key, map to a canonical UUID externally if needed.
- **Missing-data sentinels.** `--`, `NA`, `nan`, empty string, `None`, `0` (sometimes!) all mean "missing" depending on the provider. Treat them as `None` in canonical fields. Never fabricate.
- **Duplicate rows.** Some providers' exports include polling artefacts where the same snapshot appears multiple times at the same timestamp. Adapters can either dedupe or pass them through; downstream code is robust to either.
- **Auxiliary channels.** BLE fuel sensors, temperature probes, custom I/O ports often arrive as a JSON blob in one column. Parse it; promote relevant values to canonical fields; preserve the raw blob in `provider_extras` for traceability.
- **Driver events vs telemetry rows.** Some providers ship harsh-braking events inline with positions; others use separate endpoints. Two `TelematicsAdapter` subclasses sharing one `name` is fine — one for positions, one for events.

## Testing

Mirror `tests/test_trakzee_adapter.py`. The non-negotiables:

1. A `conftest.py` fixture with a realistic provider row.
2. Tests for: valid row → expected canonical event, missing data → `None` fields, edge cases that bit you while developing.
3. Aim for 90%+ adapter coverage. Adapters are the most failure-prone part of the framework because real data is always messier than the docs suggest.

## When to upstream

If your provider is one others would want — Samsara, Geotab, common OBD-II gateways, regional operators — open a PR. Roughly:

- `src/siphyy/adapters/<provider>.py` — the adapter, with a top-of-file comment listing any provider quirks that will bite future maintainers.
- `tests/test_<provider>_adapter.py` — the tests.
- An optional install group in `pyproject.toml` for any extra dependencies (`pandas`, `httpx`, etc.).
- An update to the [supported providers](../index.md#what-it-does) list in the README.

We're happy to land adapters even if they're partial — better an 80% adapter that handles the common case than a stub.
