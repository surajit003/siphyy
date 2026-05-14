# Your first pipeline

The bundled quickstart runs the full pipeline against synthetic sample data — schema, adapter, detector, agent — and prints the resulting `FuelAnomalyReport`s. It's the fastest way to see what siphyy actually does.

## Run it

From the repo root:

```bash
uv run python examples/quickstart.py
```

Output (abridged):

```
Loaded 17 Trakzee-shaped rows from sample_trakzee.json
LLM client: MockLLMClient (no API key in env)

Canonical events:  17
Tier 1 fires:      2

────────────────────────────────────────────────────────────────────────
Vehicle:     trakzee:354000000000001
Detector:    fuel_siphonage
Verdict:     likely_siphonage  (confidence 92%)
Summary:     Active siphonage strongly suggested — pattern matches fuel_theft_0001.
Reasoning:   The drop magnitude (47%) and elapsed time (18 minutes) almost
             exactly match historical case fuel_theft_0001 ...
────────────────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────────────────
Vehicle:     trakzee:354000000000002
Verdict:     likely_false_positive  (confidence 78%)
Summary:     Pattern matches post-climb fuel settling — likely sensor artifact.
...
────────────────────────────────────────────────────────────────────────
```

## What just happened

The sample dataset (`apps/demo/data/sample_trakzee.json`) is 17 synthetic Trakzee-shaped rows spanning three vehicles. Two scenarios are baked into it:

- **SAMPLE-001** — depot parking + a 47% fuel drop in 18 minutes while engine off. This matches the seed case `fuel_theft_0001` (real siphonage). Tier 1 fires; Tier 2 calls it `likely_siphonage`.
- **SAMPLE-002** — vehicle climbs a 95m grade, parks at the top, then the fuel reading drops 18% in 7 minutes as fuel settles. Tier 1 fires; Tier 2 (via the seed case `fuel_theft_0006`) calls it `likely_false_positive`.
- **SAMPLE-003** — routine route operation, no detection event. Provides background variety.

The `MockLLMClient` returns realistic pre-written verdicts so the demo works without an API key. The moment you add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` to your environment (`.env` works), the quickstart auto-detects it and calls the real LLM instead.

## Try it with a real LLM

```bash
# .env at the repo root
OPENAI_API_KEY=sk-...
```

Re-run:

```bash
uv run python examples/quickstart.py
```

The output now shows `LLM client: OpenAI (gpt-4o-mini)` and the verdicts come from a live call. Replace with `ANTHROPIC_API_KEY` to use Claude — auto-detection prefers OpenAI if both are present; remove the OpenAI key to force Anthropic.

## Inline equivalent

The quickstart is the same code the README's snippet shows:

```python
from siphyy.adapters import TrakzeeAdapter
from siphyy.agents import FuelAnomalyAgent, OpenAILLMClient
from siphyy.detectors import FuelSiphonageDetector
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase

adapter = TrakzeeAdapter()
detector = FuelSiphonageDetector()
agent = FuelAnomalyAgent(
    llm_client=OpenAILLMClient(),
    case_base=CaseBase(SEED_CASES),
)

for event in adapter.adapt(trakzee_rows):
    if (interesting := detector.process(event)) and (report := agent.process(interesting)):
        print(report.assessment, report.confidence, report.summary)
```

Three lines of setup, one for-loop. The rest of the framework is just making sure those four objects compose cleanly across providers.

## Or watch it run in a browser

`apps/demo/app.py` is a Streamlit visualiser that shows every step including the actual LLM prompts. Run locally:

```bash
uv run streamlit run apps/demo/app.py
```

Or use the [live deployment](https://huggingface.co/spaces/surajit003/siphyy) — same thing, no install.

Next: [write an adapter for your own provider →](writing-an-adapter.md)
