# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial canonical event schema (`TelemetryReading`, `DriverEvent`)
- `TrakzeeAdapter` — first reference provider adapter
- Case base schema and 5 seed cases for fuel siphonage
- pyproject.toml with full tool config (ruff, mypy, pytest, coverage)
- GitHub Actions CI workflow
- Pre-commit hooks

### Planned
- `FuelSiphonageDetector` (Tier 1)
- `FuelAnomalyAgent` (Tier 2 LLM agent)
- `SamsaraAdapter`, `GeotabAdapter`
- pgvector-backed case base for production use
- CLI: `siphyy run`, `siphyy validate-adapter`

## [0.1.0] - 2026-05-XX

Initial alpha release. Schema and Trakzee adapter only.
