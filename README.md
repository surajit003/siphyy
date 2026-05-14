# Siphyy

> Open-source agentic framework for fleet telematics analytics — fuel anomaly detection, predictive maintenance, and driver behavior intelligence, with a provider-agnostic canonical schema and structured LLM reasoning.

[![CI](https://github.com/siphyy/siphyy-core/actions/workflows/ci.yml/badge.svg)](https://github.com/siphyy/siphyy-core/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Live demo on HuggingFace](https://img.shields.io/badge/🤗_demo-Spaces-yellow.svg)](https://huggingface.co/spaces/surajit003/siphyy-demo)

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

The fastest way to see the framework in action:

```bash
git clone https://github.com/siphyy/siphyy-core.git
cd siphyy-core
uv sync                              # installs everything incl. dev tools
uv run python examples/quickstart.py
```

The quickstart loads `examples/data/sample_trakzee.json` (17 anonymised, synthetic rows), runs the full pipeline, and prints structured fuel-anomaly reports. It auto-detects which LLM provider to use:

- `OPENAI_API_KEY` in env → uses `OpenAILLMClient` (real call against `gpt-4o-mini`)
- `ANTHROPIC_API_KEY` in env → uses `AnthropicLLMClient` (real call against `claude-haiku-4-5`)
- Neither → uses `MockLLMClient` with realistic canned verdicts, so the demo works with **zero setup**

Drop a `.env` at the repo root with your key(s) and the quickstart picks them up automatically (`python-dotenv` is in the dev extras).

### Install just the library

```bash
pip install "siphyy[trakzee,llm]"
# or
uv pip install "siphyy[trakzee,llm]"
```

The minimal in-code version of what the quickstart runs:

```python
from siphyy.adapters import TrakzeeAdapter
from siphyy.agents import FuelAnomalyAgent, OpenAILLMClient
from siphyy.detectors import FuelSiphonageDetector
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase

# 1. Translate raw provider rows into canonical TelemetryReading events.
adapter = TrakzeeAdapter()

# 2. Tier 1: cheap, deterministic rules surface candidates.
detector = FuelSiphonageDetector()

# 3. Tier 2: an LLM-grounded agent interprets each candidate against
#    historical cases. The LLMClient is pluggable — swap OpenAILLMClient
#    for an Anthropic / Gemini / Ollama implementation without touching
#    agent code (see "Bring your own LLM" below).
agent = FuelAnomalyAgent(
    llm_client=OpenAILLMClient(),  # reads OPENAI_API_KEY from env
    case_base=CaseBase(SEED_CASES),
)

for event in adapter.adapt(trakzee_rows):
    if (interesting := detector.process(event)) and (report := agent.process(interesting)):
        print(report.assessment, report.confidence, report.summary)
```

### Bring your own LLM

`LLMClient` is a `Protocol` with a single method. To use a different provider, implement it in ~20 lines:

```python
from pydantic import BaseModel
from siphyy.agents import LLMClient

class MyAnthropicClient:  # satisfies LLMClient structurally
    def complete[T: BaseModel](self, *, system, user, response_model: type[T]) -> T:
        ...  # call Anthropic's tool-use endpoint, return response_model(**parsed)
```

The agent itself doesn't import `anthropic` or `openai` — only the client implementation does, so optional extras stay optional.

## Why open source

The framework is Apache 2.0 and always will be. The plumbing — canonical schema, adapters, detectors, agent code — is the commodity. What we sell separately is the **Siphyy Knowledge Pack**: curated case bases, indexed OEM manuals, calibrated detection thresholds, and the enterprise dashboard. You can use the OSS framework without ever paying us a cent.

## Writing your own adapter

The whole point of the canonical schema is that you don't have to wait for us to support your telematics provider. Subclass `TelematicsAdapter` in ~50 lines and you're integrated. See [docs/writing-adapters.md](docs/writing-adapters.md) — `TrakzeeAdapter` is the reference implementation.

## Project status

Alpha. The canonical schema, the Trakzee adapter, the `FuelSiphonageDetector`, and the `FuelAnomalyAgent` are stable today. Additional provider adapters, additional detectors and agents, the CLI, and the storage backend are still in active development — track [CHANGELOG.md](CHANGELOG.md) for what lands when. Pin to a specific version until 1.0.

## License

Apache 2.0. See [LICENSE](LICENSE).
