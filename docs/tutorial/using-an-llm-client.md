# Using an LLM client

Siphyy's Tier 2 agents call the LLM through an `LLMClient` Protocol — a one-method interface. Two reference implementations ship with the library; bringing your own provider is ~20 lines.

## The reference implementations

```python
from siphyy.agents import OpenAILLMClient, AnthropicLLMClient, MockLLMClient
```

| Client | Provider | When to use |
|---|---|---|
| `OpenAILLMClient` | OpenAI structured outputs (`client.beta.chat.completions.parse`) | Default. Most cost-effective with `gpt-4o-mini`. |
| `AnthropicLLMClient` | Anthropic Messages API with forced tool-use | Stronger reasoning on `claude-sonnet`/`claude-opus`. |
| `MockLLMClient` | Pre-built canned responses | Tests, CI, demos without API keys. |

All three satisfy the same Protocol. Swap them at the call site; no other code changes.

## OpenAI

```python
from siphyy.agents import OpenAILLMClient

client = OpenAILLMClient(
    model="gpt-4o-mini-2024-07-18",
    api_key=None,  # falls back to OPENAI_API_KEY env var
)
```

`gpt-4o-mini-2024-07-18` is the cheapest model that supports OpenAI's strict structured-output mode. For harder reasoning, try `gpt-4o-2024-08-06` or whatever's current.

You can also point at OpenAI-compatible endpoints (Ollama, vLLM, Together.ai, Groq) via `base_url`:

```python
client = OpenAILLMClient(
    model="llama-3.1-70b-instruct",
    base_url="http://localhost:11434/v1",  # local Ollama
    api_key="ollama",                       # any non-empty string
)
```

## Anthropic

```python
from siphyy.agents import AnthropicLLMClient

client = AnthropicLLMClient(
    model="claude-haiku-4-5-20251001",  # fast and cheap; sonnet/opus for harder calls
    api_key=None,  # falls back to ANTHROPIC_API_KEY
)
```

Anthropic doesn't ship a parse-Pydantic endpoint, so `AnthropicLLMClient` uses forced tool-use under the hood: it converts your response model's JSON schema into a tool definition, forces the model to call it, then parses the tool input back into your model. Same Protocol surface — you don't see any of that.

## Bring your own provider

`LLMClient` is a `Protocol` (PEP 544 structural typing). You don't subclass it; you write a class with a `complete` method matching the signature.

```python
from pydantic import BaseModel
from siphyy.agents import LLMClient

class MyClient:  # implicitly implements LLMClient
    def __init__(self, ...) -> None:
        ...

    def complete[T: BaseModel](
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        # 1. Send (system, user) to your provider
        # 2. Constrain the output to response_model.model_json_schema()
        # 3. Parse the response back into response_model
        # 4. Return the parsed instance
        ...
```

The four steps are the same regardless of provider — the implementation differences are entirely about how each API exposes structured outputs.

Real implementations are short — see [`openai_client.py`](https://github.com/surajit003/siphyy/blob/main/src/siphyy/agents/openai_client.py) (~80 lines) and [`anthropic_client.py`](https://github.com/surajit003/siphyy/blob/main/src/siphyy/agents/anthropic_client.py) (~95 lines). Most of the line count is docstrings.

## Drop your client into an agent

The agent doesn't care which `LLMClient` it got — that's the whole point of the Protocol.

```python
from siphyy.agents import FuelAnomalyAgent
from siphyy.schema import CaseBase
from siphyy.knowledge import SEED_CASES

agent = FuelAnomalyAgent(
    llm_client=MyClient(),         # ← any LLMClient
    case_base=CaseBase(SEED_CASES),
)
```

## Testing without burning credits

Use `MockLLMClient` with canned responses for unit tests:

```python
from siphyy.agents import MockLLMClient
from siphyy.agents.fuel_anomaly import _LLMVerdict

mock = MockLLMClient([
    _LLMVerdict(
        assessment="likely_siphonage",
        confidence=0.9,
        summary="...",
        reasoning="...",
        recommended_actions=[],
        referenced_case_ids=[],
    ),
])
agent = FuelAnomalyAgent(llm_client=mock, case_base=CaseBase())
```

Responses are popped from the list in order. If the agent tries to call `complete` more times than you supplied responses, the mock raises `RuntimeError` — failing loud is better than silently breaking.

The integration tests under `tests/integration/` do the opposite: they hit the real APIs but only when the relevant env var is set, so they skip cleanly in environments without keys.

---

You've now seen everything end-to-end. From here:

- [Concepts](../concepts/index.md) for the *why* behind the architecture
- [How-to recipes](../how-to/index.md) for problem-driven snippets
- [API reference](../reference/index.md) for the auto-generated method docs
