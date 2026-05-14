---
hide:
  - navigation
---

# Siphyy

> Open-source agentic framework for fleet telematics — fuel anomaly detection, predictive maintenance, and driver-behaviour intelligence, with a provider-agnostic canonical schema and structured LLM reasoning.

[![CI](https://github.com/surajit003/siphyy/actions/workflows/ci.yml/badge.svg)](https://github.com/surajit003/siphyy/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![🤗 Live demo](https://img.shields.io/badge/🤗_demo-Spaces-yellow.svg)](https://huggingface.co/spaces/surajit003/siphyy)

## What it does

Fleet operations data lives in dozens of telematics platforms — Samsara, Geotab, Trakzee, Verizon Connect, regional providers, raw OBD-II streams — each with its own schema, polling cadence, and quirks. Siphyy normalises all of them into a single canonical event stream, runs cheap deterministic detectors over that stream, and uses an LLM agent grounded in a curated case base to interpret only the events that matter.

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

Read [the architecture concepts](concepts/architecture.md) for the long version.

## Try it in 5 minutes

```bash
git clone https://github.com/surajit003/siphyy.git
cd siphyy
uv sync
uv run python examples/quickstart.py
```

Or hit the [live demo](https://huggingface.co/spaces/surajit003/siphyy) — upload a Trakzee export (or use the bundled sample), watch the pipeline run step by step, see every prompt the LLM receives.

## Where to next

- **New here?** Start with the [tutorial](tutorial/index.md) — install, then a first pipeline, then writing your own adapter.
- **Want the big picture?** Read the [architecture concepts](concepts/architecture.md).
- **Already using siphyy?** The [API reference](reference/index.md) is auto-generated from the source.
- **Want to contribute?** See the [contributing guide](about/contributing.md).

## Why open source

The framework is Apache 2.0 and always will be. The plumbing — canonical schema, adapters, detectors, agent code — is the commodity. What we sell separately is the **Siphyy Knowledge Pack**: curated case bases, indexed OEM manuals, calibrated detection thresholds, and the enterprise dashboard. You can use the OSS framework without ever paying us a cent.

## Project status

Alpha. The canonical schema, the `TrakzeeAdapter`, the `FuelSiphonageDetector`, and the `FuelAnomalyAgent` are stable today. Additional provider adapters, additional detectors and agents, the CLI, and the storage backend are still in active development. Pin to a specific version until 1.0.
