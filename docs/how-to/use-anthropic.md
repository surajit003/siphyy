# Use Anthropic instead of OpenAI

Same agent, different client. The provider-neutral `LLMClient` Protocol means the agent doesn't import `openai` or `anthropic` directly — only the client does.

## Switch the client

```python
from siphyy.agents import (
    FuelAnomalyAgent,
    AnthropicLLMClient,  # ← instead of OpenAILLMClient
)
from siphyy.schema import CaseBase
from siphyy.knowledge import SEED_CASES

agent = FuelAnomalyAgent(
    llm_client=AnthropicLLMClient(),  # picks up ANTHROPIC_API_KEY from env
    case_base=CaseBase(SEED_CASES),
)
```

That's it. The agent's `process()` call is unchanged. Reports come back with the same `FuelAnomalyReport` shape.

## Pick a model

Defaults are:

| Client | Default model |
|---|---|
| `OpenAILLMClient` | `gpt-4o-mini-2024-07-18` |
| `AnthropicLLMClient` | `claude-sonnet-4-6` |

Override for speed/cost:

```python
AnthropicLLMClient(model="claude-haiku-4-5-20251001")
```

Override for quality on harder reasoning:

```python
AnthropicLLMClient(model="claude-opus-4-7")
```

`AnthropicLLMClient` uses forced tool-use under the hood for structured outputs — that works across the entire Claude 4.x family.

## API keys

`AnthropicLLMClient()` falls back to `ANTHROPIC_API_KEY` from the environment if you don't pass `api_key=` explicitly. A `.env` at the repo root is the cleanest pattern for local development:

```
ANTHROPIC_API_KEY=sk-ant-...
```

The quickstart, tests, and demo app all soft-load `.env` if `python-dotenv` is installed (it's part of the `[dev]` extras).

## Run both side by side

For comparison work — same prompts, same cases, different LLM — keep one of each:

```python
openai_agent = FuelAnomalyAgent(OpenAILLMClient(), CaseBase(SEED_CASES))
anthropic_agent = FuelAnomalyAgent(AnthropicLLMClient(), CaseBase(SEED_CASES))

for event in interesting:
    a = openai_agent.process(event)
    b = anthropic_agent.process(event)
    print(event.vehicle_id, a.assessment, b.assessment, "match" if a.assessment == b.assessment else "DIFFER")
```

Useful when calibrating which model is right for your fleet's noise profile.

## What if you want a different provider entirely?

`LLMClient` is a `Protocol`. Write your own — see [using an LLM client](../tutorial/using-an-llm-client.md#bring-your-own-provider) in the tutorial.
