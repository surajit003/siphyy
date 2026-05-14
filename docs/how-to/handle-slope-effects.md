# Handle slope-effect false positives

A truck parked at the top of a climb shows a 15–25% "fuel drop" in the minutes after parking. The cause is mechanical: fuel that pooled at the back of the tank during the climb redistributes once engine vibration stops. No fuel left the tank. To the `FuelSiphonageDetector`, it looks identical to siphonage.

This is the seed case `fuel_theft_0006` ("post-climb settling, ruled false positive after manual dip"). Here's how the framework deals with it, and what your deployment should add on top.

## Out of the box: it's handled at Tier 2

The framework's design encodes the handling in three places:

1. **`TelemetryReading` carries the orientation signals** that matter — `pitch_deg`, `roll_deg`, `altitude_m`. Optional, populated by adapters that have access (Teltonika AVL IDs 256/257, Samsara accelerometer, etc.); `None` otherwise.
2. **`FuelSiphonageDetector` includes the slope context in `evidence`** when it fires — `prior_altitude_m`, `current_altitude_m`, `altitude_delta_m`, `prior_pitch_deg`, `current_pitch_deg`, `current_roll_deg`. Only the fields actually known land in evidence; nothing is fabricated.
3. **The seed case `fuel_theft_0006` is loaded into the agent's prompt every time it runs.** The LLM sees the pattern alongside the current event's evidence and rules it out where appropriate.

The Tier 1 detector itself **does not suppress firing** based on slope. That's deliberate — Tier 1 is recall-oriented; Tier 2 (with the seed case and the evidence in hand) is the right layer to make the call.

## If your adapter has pitch / roll, ship it

Some telematics devices expose pitch and roll directly via accelerometer channels — Teltonika FMx via AVL IDs 256 and 257, Queclink, OEM CAN integrations. If yours does, populate `pitch_deg` and `roll_deg` on every emitted `TelemetryReading`. The agent then has real orientation data in evidence, not just inferred altitude deltas.

If your adapter doesn't (the default Trakzee export doesn't, for example), `pitch_deg` stays `None` and the agent leans on altitude trajectory and the seed case prose. That works — just less precisely.

## If you have a hilly-route fleet, add cases

The single highest-leverage thing you can do is add a slope-effect case from your *own* operation to the case base. Each case is one Pydantic literal:

```python
IncidentCase(
    case_id="fuel_theft_<your_id>",
    category="false_positive",
    severity="low",
    region="<your region>",
    vehicle_type="<your vehicle type>",
    summary="<describe the event in the prose register a Tier 1 detector would use>",
    diagnosis="<what was actually happening, established by investigation>",
    resolution="<concrete action taken>",
    lessons=[
        "<generalisable pattern 1>",
        "<generalisable pattern 2>",
    ],
    tags=["false_positive", "slope_effect", "<your route descriptor>"],
    confidence=0.95,
    occurred_at=datetime(...),
)
```

The agent retrieves these the next time it runs. Add three or four cases from your real operation and the LLM's verdicts shift noticeably — it's pattern-matching on cases close to the deployment, not on generic ones from a paper somewhere.

## If you're seeing too many slope false positives at Tier 1

Tune the detector's defaults at instantiation time:

```python
FuelSiphonageDetector(
    threshold_pct=0.25,   # 0.15 is the default
    max_minutes=30,       # 60 is the default
)
```

Tightening these reduces Tier 1 firing rate but also risks missing real siphonage. The framework's bias is toward catching more at Tier 1 and filtering at Tier 2 — only raise the threshold if your Tier 2 cost is becoming a problem.

## What not to do

**Don't add slope-suppression logic to the detector.** It's tempting — "if `altitude_delta > X`, suppress firing" — but it bakes a physical model into Tier 1 that should live as Tier 2 reasoning. The seed cases are the right place to teach the LLM about these patterns; the detector's job is to surface candidates, not adjudicate physical causes.

This is the principle the [Tier 1 vs Tier 2 concept page](../concepts/tier-1-vs-tier-2.md) makes concrete: every time you're tempted to add a "smarter" rule to Tier 1, prefer adding a seed case to the case base instead.
