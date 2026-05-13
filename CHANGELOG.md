# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial canonical event schema (`TelemetryReading`, `DriverEvent`)
- Fuel and environment fields on `TelemetryReading`: `fuel_level_percent`,
  `fuel_level_liters`, `fuel_level_raw`, `fuel_sensor_type`,
  `tank_capacity_liters`, `ambient_temperature_c`
- `TrakzeeAdapter` — first reference provider adapter; promotes BLE fuel
  readings into canonical fields rather than hiding them in `provider_extras`
- `InterestingEvent` schema — the payload Tier 1 detectors emit
- `Detector` ABC, `StateStore` Protocol, and `InMemoryStateStore`
- `FuelSiphonageDetector` (Tier 1) — fires on fuel-level drops while at rest
- `Agent` ABC + `LLMClient` Protocol — provider-neutral Tier 2 interface
- `OpenAILLMClient` (using OpenAI structured outputs) as the first
  concrete `LLMClient`; `MockLLMClient` for tests
- `FuelAnomalyAgent` (Tier 2) — retrieves historical cases and produces a
  structured `FuelAnomalyReport`
- Case base schema and 5 seed cases for fuel siphonage
- pyproject.toml with full tool config (ruff, mypy, pytest, coverage)
- GitHub Actions CI workflow
- Pre-commit hooks

### Planned
- Anthropic / Gemini / Ollama `LLMClient` implementations
- `MaintenanceRiskAgent` (Tier 2)
- `SamsaraAdapter`, `GeotabAdapter`
- pgvector-backed case base for production use
- Redis-backed `StateStore` implementation
- CLI: `siphyy run`, `siphyy validate-adapter`

## [0.1.0] - 2026-05-XX

Initial alpha release. Canonical schema, Trakzee adapter,
`FuelSiphonageDetector` (Tier 1), and `FuelAnomalyAgent` (Tier 2) with a
pluggable `LLMClient` Protocol and `OpenAILLMClient` reference
implementation.
