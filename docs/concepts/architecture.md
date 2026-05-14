# Architecture

Four layers, one direction of data flow. Each layer has a single job.

```
                    Telematics providers              LLM providers
                    ┌─────────────────────┐           ┌──────────────────────┐
                    │ Trakzee  ← shipped  │           │ OpenAI    ← shipped  │
                    │ Samsara             │           │ Anthropic ← shipped  │
                    │ Geotab              │           │ Gemini               │
                    │ OBD-II              │           │ Ollama / vLLM        │
                    └─────────┬───────────┘           └──────────┬───────────┘
                              │                                  │
                  implement TelematicsAdapter           implement LLMClient
                              │                                  │
                              ▼                                  ▼
                    ┌─────────────────┐    ┌──────────────────┐  │
   Raw rows ───────▶│ Adapter         │───▶│ TelemetryReading │──┴──▶ FuelSiphonageDetector ──▶ InterestingEvent ──▶ FuelAnomalyAgent ──▶ FuelAnomalyReport
                    └─────────────────┘    └──────────────────┘            ▲                                            │
                                                                           │                                            │
                                                                  uses StateStore                                 uses LLMClient
                                                                  (in-memory dev,                                       │
                                                                   Redis prod)                                          │
                                                                           └────────────────────────────────────────────┘
```

## The four layers

### 1. Adapter

Translates raw provider data (`pandas.DataFrame` rows, JSON dicts, whatever) into canonical events. Lives at `src/siphyy/adapters/`.

Key constraint: **adapters are pure functions of their input**. No network calls, no DB writes, no shared mutable state. They convert units (km/h, °C, UTC), they map provider-specific status codes to canonical enums, and they leave fields `None` when the provider doesn't expose them. That's it.

The reference implementation is [`TrakzeeAdapter`](https://github.com/surajit003/siphyy/blob/main/src/siphyy/adapters/trakzee.py). Read it before writing your own — it covers every pattern you'll need: unit conversion, timezone normalisation, missing-data handling, auxiliary channel parsing, vehicle-ID mapping.

### 2. Canonical schema

The contract everything past the adapter speaks. Lives at `src/siphyy/schema/`.

Two event types today:

- `TelemetryReading` — point-in-time vehicle state. Position, motion, fuel, electrical, orientation.
- `DriverEvent` — discrete driver-attributable events (harsh brake, speeding, idling).

Both are `BaseEvent` subclasses, both frozen (immutable), both reject unknown fields. The schema is small on purpose — it's a contract, not a kitchen sink.

Read [canonical schema](canonical-schema.md) for the field-by-field reasoning.

### 3. Tier 1 detector

Cheap, deterministic rules. Lives at `src/siphyy/detectors/`.

A detector takes a canonical event, consults its per-vehicle state, and emits an `InterestingEvent` if a rule fires. The whole layer is bounded by "no LLM calls" — that's what makes it cheap enough to run on every telemetry row in real time.

Tier 1's job is *recall*: surface the candidates. False positives are fine here.

### 4. Tier 2 agent

LLM-grounded interpretation. Lives at `src/siphyy/agents/`.

An agent takes an `InterestingEvent`, retrieves relevant cases from the `CaseBase`, builds a prompt that grounds the LLM in historical precedent, and calls the configured `LLMClient`. The output is a structured Pydantic report.

Tier 2's job is *precision*: rule out the false positives that Tier 1 surfaced. The LLM has the historical cases (including known false-positive patterns like thermal contraction and slope effects) to make defensible calls.

## Why this shape

### Why split into tiers?

LLM calls cost real money (~$0.001–0.01 each on cheap models) and take seconds. Running an LLM on every telemetry row for a 200-truck fleet polling every minute is ~$100k/month. The Tier 1 filter cuts the data volume by ~1000x — only the candidate events go to the LLM. The Tier 2 cost on a real fleet is dollars-per-day, not thousands-per-month.

### Why provider-agnostic at every layer?

Telematics providers have wildly different schemas, polling cadences, and quirks. Hard-coding to one provider makes the framework a single-customer thing. Detectors and agents that reason in canonical types work against any adapter.

LLM providers are the same story. OpenAI's structured outputs and Anthropic's tool-use look superficially different, but they produce the same Pydantic-validated objects to the agent layer.

### Why ground the LLM in cases?

A bare LLM hallucinates. Confidently. A case-grounded LLM cites historical precedent and can explicitly reason about which cases match the current event and which don't. The seed case `fuel_theft_0003` (thermal contraction) is in the prompt every time the agent runs — that's how the framework knows to rule out overnight-temperature-induced "drops" without anyone writing thermal-contraction logic.

Read [Tier 1 vs Tier 2](tier-1-vs-tier-2.md) for the precision/recall trade-off in more detail.

## What's deliberately not in this picture

- **Storage.** The framework produces events and reports; what you do with them — write to Postgres, push to Kafka, ship to a dashboard — is your call. There's no built-in store. A pgvector-backed `CaseBase` is on the roadmap, but that's for retrieval, not event persistence.
- **Authentication, multi-tenancy, billing.** These are application concerns, not framework concerns. The framework is a library; wrap it in whatever service shape your business needs.
- **Real-time streaming.** Adapters take iterables; if you want streaming, hand them a generator that yields rows as they arrive. The framework doesn't bring its own message bus.
