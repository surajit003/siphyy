# Writing a detector

Detectors are Tier 1. They scan the canonical event stream, hold per-vehicle state, and emit `InterestingEvent`s when a rule fires. They are deliberately cheap and recall-oriented — Tier 2 (the agent) handles precision.

## The contract

```python
from siphyy.detectors.base import Detector
from siphyy.schema import CanonicalEvent, InterestingEvent

class MyDetector(Detector):
    name = "my_detector"

    def process(self, event: CanonicalEvent) -> InterestingEvent | None:
        # Decide whether THIS event should fire. Return None for no, or
        # an InterestingEvent for yes.
        ...
```

Two requirements:

- **`name`** is a short, stable identifier (no spaces). It ends up in `InterestingEvent.detector_name` and in `StateStore` keys.
- **`process()`** returns either `None` (irrelevant event, or rule didn't fire) or an `InterestingEvent` (rule fired).

That's the entire surface. Everything else — thresholds, state, prompts, evidence formatting — is your detector's internal concern.

## State

Detectors need state per vehicle (e.g. "what was the last fuel reading I saw for this vehicle?"). The base class gives you a `StateStore` ready to use:

```python
class MyDetector(Detector):
    name = "my_detector"

    def process(self, event):
        if not isinstance(event, TelemetryReading):
            return None

        key = self._state_key(event.vehicle_id)  # "my_detector:trakzee:abc-123"
        prior = self.state.get(key)              # dict | None
        self.state.set(key, {                    # always overwrite with the new state
            "last_seen_at": event.timestamp.isoformat(),
            "some_value": event.something,
        })

        if prior is None:
            return None  # no baseline yet
        # ... compare current event to prior, decide whether to fire ...
```

`StateStore` is a `Protocol` — `InMemoryStateStore` is the default for tests and single-process use. Production deployments pass in a Redis-backed implementation. Your detector code doesn't care.

## Three rules of well-behaved detectors

1. **Be recall-oriented.** Tier 1 should fire generously. Tier 2 has the LLM and the case base to rule out false positives. If you find yourself adding a fourth conditional to avoid a false positive at Tier 1, stop — that's a candidate for a new seed case in the case base instead.

2. **Put context in `evidence`, not in `summary`.** The `summary` field is a one-line human-readable string. The `evidence` dict is where you stash the numbers Tier 2 needs to reason: the prior reading, the delta, the elapsed time, the engine state, etc. Tier 2's LLM gets all of `evidence` in its prompt.

3. **Bail on irrelevant events fast.** `isinstance(event, TelemetryReading)` first, then check the fields you actually need (`event.fuel_level_raw is None` → return). A detector shouldn't trip over `DriverEvent`s or rows with missing data.

## Worked example: `FuelSiphonageDetector`

The simplest production detector in the framework is `FuelSiphonageDetector`. Its rule is one paragraph:

> Fire when `fuel_level_raw` drops by ≥ `threshold_pct` between two consecutive readings of the same vehicle, within `max_minutes`, while `engine_state ∈ {stopped, idle}` and `ignition_on=False`.

Source: [`src/siphyy/detectors/fuel_siphonage.py`](https://github.com/surajit003/siphyy/blob/main/src/siphyy/detectors/fuel_siphonage.py).

Notice what it *doesn't* do: ambient-temperature suppression, slope-effect suppression, route-deviation cross-references. Those all belong in Tier 2's reasoning, grounded in seed cases like `fuel_theft_0003` (thermal contraction) and `fuel_theft_0006` (slope effect).

## Testing your detector

Mirror `tests/test_fuel_siphonage_detector.py`:

1. A helper that builds minimal `TelemetryReading` instances.
2. A test per rule clause (fire when X, don't fire when not-X).
3. A test that confirms state is preserved across calls.
4. A test that confirms it's a no-op on `DriverEvent` and on missing-data rows.

Aim for high coverage on the rule's branches. Detectors are the place where bugs cost most: false negatives let real theft through, false positives erode user trust.

## Registering your detector

There's no plugin registry. Detectors are just classes — instantiate yours wherever you assemble the pipeline:

```python
from my_package.detectors import MyDetector

detectors = [
    FuelSiphonageDetector(),
    MyDetector(),
]
for event in adapter.adapt(rows):
    for detector in detectors:
        if interesting := detector.process(event):
            agent.process(interesting)
```

If your detector is something other operators would want, open a PR to add it under `src/siphyy/detectors/`. The bar is: a clear rule, tests covering the firing and non-firing branches, and a seed-case example showing what kind of cases the agent should expect to see.

Next: [pick an LLM provider →](using-an-llm-client.md)
