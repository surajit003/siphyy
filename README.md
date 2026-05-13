# Siphyy

> Open-source agentic framework for fleet telematics analytics — fuel anomaly detection, predictive maintenance, and driver behavior intelligence, with a provider-agnostic canonical schema and structured LLM reasoning.

[![CI](https://github.com/siphyy/siphyy-core/actions/workflows/ci.yml/badge.svg)](https://github.com/siphyy/siphyy-core/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## What it does

Fleet operations data lives in dozens of telematics platforms (Samsara, Geotab, Trakzee, Verizon Connect, regional providers, raw OBD-II streams) — each with its own schema, polling cadence, and quirks. Siphyy normalises all of them into a single canonical event stream, runs cheap deterministic detectors over that stream, and uses an LLM agent grounded in a curated case base to interpret only the events that matter.

The output is structured, auditable, and ready to be wired into fleet management systems — not free-text mechanic advice.

## Architecture in 30 seconds

```
   [Telematics Provider]    ←  Samsara, Geotab, Trakzee, OBD-II, ...
            │
            ▼
   [Adapter]                ←  Translates provider → canonical schema
            │
            ▼
   [Tier 1: Detector]       ←  Cheap rule-based detection. No LLMs.
            │
            ▼ (interesting events only)
   [Tier 2: LLM Agent]      ←  Agentic RAG over case base + OEM manuals
            │
            ▼
   [Structured Output]      ←  FuelAnomalyReport, MaintenanceRiskReport, ...
```

## Quickstart

```bash
# Install with the Trakzee adapter
pip install "siphyy[trakzee,llm]"

# Or with uv
uv pip install "siphyy[trakzee,llm]"
```

```python
from siphyy.adapters import TrakzeeAdapter
from siphyy.schema import CanonicalEvent

# 1. Translate provider data into canonical events
adapter = TrakzeeAdapter()
events = list(adapter.adapt(trakzee_rows))  # provider-specific dicts in, canonical out

# 2. Hand them to a Tier 1 detector
from siphyy.detectors import FuelSiphonageDetector
detector = FuelSiphonageDetector()
for event in events:
    if anomaly := detector.process(event):
        print(anomaly)
```

## Why open source

The framework is Apache 2.0 and always will be. The plumbing — canonical schema, adapters, detectors, agent code — is the commodity. What we sell separately is the **Siphyy Knowledge Pack**: curated case bases, indexed OEM manuals, calibrated detection thresholds, and the enterprise dashboard. You can use the OSS framework without ever paying us a cent.

## Writing your own adapter

The whole point of the canonical schema is that you don't have to wait for us to support your telematics provider. Subclass `TelematicsAdapter` in ~50 lines, run `siphyy validate-adapter`, and you're integrated. See [docs/writing-adapters.md](docs/writing-adapters.md).

## Project status

Alpha. The schema, the Trakzee adapter, and the fuel siphonage detector are stable. The LLM agent, additional adapters, and the storage backend are in active development. Pin to a specific version until 1.0.

## License

Apache 2.0. See [LICENSE](LICENSE).
