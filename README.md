# Siphyy

> Open-source agentic framework for fleet telematics analytics — fuel anomaly detection, predictive maintenance, and driver behavior intelligence, with a provider-agnostic canonical schema and structured LLM reasoning.

[![PyPI](https://img.shields.io/pypi/v/siphyy.svg)](https://pypi.org/project/siphyy/)
[![CI](https://github.com/surajit003/siphyy/actions/workflows/ci.yml/badge.svg)](https://github.com/surajit003/siphyy/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Live demo on HuggingFace](https://img.shields.io/badge/🤗_demo-Spaces-yellow.svg)](https://huggingface.co/spaces/surajit003/siphyy)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue.svg)](docs/index.md)

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

## Install

```bash
pip install "siphyy[trakzee,llm]"
# or
uv pip install "siphyy[trakzee,llm]"
```

Optional-dependency groups: `trakzee` (pandas + openpyxl for xlsx parsing), `llm` (openai + anthropic clients), `demo` (Streamlit visualiser), `storage` (pgvector — planned).

## How it works

### 1. Adapter — provider data → canonical events

Adapters translate provider-specific shapes into the canonical schema. Units (km, km/h, °C, UTC) and field names are normalised at the boundary so nothing downstream cares what wire format the data arrived in.

```python
from siphyy.adapters import TrakzeeAdapter

adapter = TrakzeeAdapter()
for event in adapter.adapt(trakzee_rows):
    print(
        event.vehicle_id,            # "trakzee:353201358420054"
        event.timestamp,             # always UTC
        event.engine_state,          # "running" / "idle" / "stopped"
        event.fuel_level_raw,        # promoted from BLE provider_extras
        event.fuel_sensor_type,      # "ble"
    )
```

Other providers ship as separate adapter classes sharing the same `name`: `SamsaraStatsAdapter` for polled telemetry and `SamsaraWebhookAdapter` for push-based alerts.

### 2. Tier 1 — canonical events → `InterestingEvent`s

Detectors are deterministic, cheap, and stateful per-vehicle. They surface candidates worth a closer look; precision is Tier 2's job.

```python
from siphyy.detectors import FuelSiphonageDetector

detector = FuelSiphonageDetector()

for event in adapter.adapt(trakzee_rows):
    if interesting := detector.process(event):
        print(interesting.severity, interesting.summary)
        # "critical Fuel sensor reading dropped 47% over 18 min while
        #  engine_state was stopped with ignition off."
```

### 3. Tier 2 — `InterestingEvent` → `FuelAnomalyReport`

The agent grounds an LLM call in retrieved historical cases (real siphonage patterns *and* known false-positive patterns like thermal contraction and slope settling) and produces a structured report.

```python
from siphyy.agents import FuelAnomalyAgent, OpenAILLMClient
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase

agent = FuelAnomalyAgent(
    llm_client=OpenAILLMClient(),       # reads OPENAI_API_KEY from env
    case_base=CaseBase(SEED_CASES),
)

for event in adapter.adapt(trakzee_rows):
    if (interesting := detector.process(event)) and (report := agent.process(interesting)):
        print(report.assessment, f"({report.confidence:.0%})")
        print(report.summary)
        print(report.reasoning)
        # assessment ∈ {"likely_siphonage", "likely_false_positive", "uncertain"}
```

### Bring your own LLM

`LLMClient` is a `Protocol` with two methods (`complete`, `embed`). Swap providers without touching agent code:

```python
from pydantic import BaseModel
from siphyy.agents import LLMClient

class MyClient:  # satisfies LLMClient structurally — no inheritance
    def complete[T: BaseModel](self, *, system, user, response_model: type[T]) -> T:
        ...  # any provider's structured-output endpoint

    def embed(self, text: str) -> list[float]:
        ...  # any provider's embeddings endpoint
```

`OpenAILLMClient` and `AnthropicLLMClient` ship in the box. The agent never imports `openai` or `anthropic`.

## Try it in 5 minutes

Either path works — pick whichever fits.

**Hosted demo** — <https://huggingface.co/spaces/surajit003/siphyy>. Upload a Trakzee export (or use the bundled sample), watch the pipeline run step by step, see every prompt the LLM receives.

**Local quickstart**:

```bash
git clone https://github.com/surajit003/siphyy.git
cd siphyy
uv sync
uv run python examples/quickstart.py
```

The quickstart loads `apps/demo/data/sample_trakzee.json` (17 synthetic rows with a planted siphonage scenario), runs the full pipeline, prints two structured reports. Auto-detects which LLM provider to use:

- `OPENAI_API_KEY` in env → real OpenAI call (defaults to `gpt-4o-mini`)
- `ANTHROPIC_API_KEY` in env → real Anthropic call (defaults to `claude-haiku-4-5`)
- Neither → `MockLLMClient` with realistic canned verdicts, **zero setup needed**

Drop a `.env` at the repo root with your keys and the quickstart picks them up.

## Why open source

The framework is Apache 2.0 and always will be. The plumbing — canonical schema, adapters, detectors, agent code — is the commodity. What we sell separately is the **Siphyy Knowledge Pack**: curated case bases, indexed OEM manuals, calibrated detection thresholds, and the enterprise dashboard. You can use the OSS framework without ever paying us a cent.

## Writing your own adapter

The whole point of the canonical schema is that you don't have to wait for us to support your telematics provider. Subclass `TelematicsAdapter` in ~50 lines and you're integrated. See [docs/writing-adapters.md](docs/writing-adapters.md) — `TrakzeeAdapter` is the reference implementation.

## Project status

Alpha. The canonical schema, the Trakzee adapter, the `FuelSiphonageDetector`, and the `FuelAnomalyAgent` are stable today. Additional provider adapters, additional detectors and agents, the CLI, and the storage backend are still in active development — track [CHANGELOG.md](CHANGELOG.md) for what lands when. Pin to a specific version until 1.0.

## License

Apache 2.0. See [LICENSE](LICENSE).
