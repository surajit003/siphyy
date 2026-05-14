# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(accumulates entries for the next release)

## [0.1.0] - 2026-05-14

Initial public alpha. End-to-end fleet telematics pipeline:
schema → adapter → Tier 1 detector → Tier 2 LLM-grounded agent.
Provider-agnostic at every layer — adding a new telematics provider
or a new LLM provider is a single-file addition, no framework
changes.

### Added

**Canonical schema** — `siphyy.schema`

- `TelemetryReading`, `DriverEvent`, `InterestingEvent` event types;
  frozen Pydantic models, `extra="forbid"`, units canonical (km, km/h,
  °C, UTC)
- Fuel + environment fields on `TelemetryReading`:
  `fuel_level_percent`, `fuel_level_liters`, `fuel_level_raw`,
  `fuel_sensor_type`, `tank_capacity_liters`, `ambient_temperature_c`
- Orientation fields `pitch_deg` and `roll_deg` — opt-in, used by the
  Tier 2 agent to rule out slope-effect false positives

**Adapters** — `siphyy.adapters`

- `TelematicsAdapter` ABC
- `TrakzeeAdapter` — first reference provider; promotes BLE fuel
  readings into canonical fields rather than hiding them in
  `provider_extras`
- `SamsaraStatsAdapter` — polled `/stats/feed` and `/stats/history`
  responses; forward-fills engine state through fuel-only timestamps
- `SamsaraWebhookAdapter` — push-based alerts (`HarshBraking`,
  `HarshAcceleration`, `DeviceSpeedAbove`); other Samsara event types
  are skipped silently

**Tier 1 detectors** — `siphyy.detectors`

- `Detector` ABC, `StateStore` Protocol, `InMemoryStateStore`
- `FuelSiphonageDetector` — fires on fuel-level drops while the
  vehicle is at rest with ignition off. Cross-provider: same detector
  fires on both Trakzee and Samsara payloads, unmodified.

**Tier 2 agents** — `siphyy.agents`

- `Agent` ABC + `LLMClient` Protocol — provider-neutral interface
- `OpenAILLMClient` (OpenAI structured outputs) and
  `AnthropicLLMClient` (Anthropic forced tool-use); `MockLLMClient`
  for tests
- `FuelAnomalyAgent` — retrieves historical cases, builds a grounded
  prompt, produces a structured `FuelAnomalyReport`
- `LLMClient.embed()` + `CaseBase.index()`/`retrieve()` — vector
  similarity retrieval against per-case embeddings. Falls back to
  category-only filtering when the embedder is unavailable
  (Anthropic has no first-party embeddings yet).

**Knowledge layer** — `siphyy.knowledge`

- `IncidentCase` schema, in-memory `CaseBase`
- 6 seed cases: 5 fuel-theft scenarios + known false-positive patterns
  (thermal contraction, post-climb slope settling)

**Examples + demo**

- `examples/quickstart.py` — 5-minute pipeline demo against bundled
  anonymised sample data, auto-detects `OPENAI_API_KEY` /
  `ANTHROPIC_API_KEY` from env or falls back to `MockLLMClient`
- Streamlit visualiser app under `apps/demo/` for HuggingFace Spaces,
  showing each pipeline step + the actual LLM prompts

**Tooling**

- `pyproject.toml` with full tool config (ruff, mypy, pytest, coverage)
- GitHub Actions: CI on Python 3.14; auto-deploy of the demo Space
  on every change; tag-triggered PyPI release workflow with OIDC
  trusted publishing
- Pre-commit hooks
- Dependabot config for `pip`, `github-actions`, and Docker
- MkDocs Material documentation site under `docs/`

**Community files**

- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
- `SECURITY.md` — private vulnerability reporting policy
- Issue and PR templates

### Planned

- Gemini / Ollama `LLMClient` implementations
- `MaintenanceRiskAgent` (Tier 2)
- `GeotabAdapter` and additional provider adapters
- pgvector-backed case base for production use
- Redis-backed `StateStore` implementation
- CLI: `siphyy run`, `siphyy validate-adapter`
