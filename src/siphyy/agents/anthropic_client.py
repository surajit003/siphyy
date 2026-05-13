"""Anthropic implementation of the `LLMClient` Protocol.

Anthropic's Messages API doesn't ship a native "parse this Pydantic
model" endpoint the way OpenAI does. The idiomatic way to get
structured output is to define a tool whose ``input_schema`` is the
JSON Schema of the response model, then force the model to call that
tool with ``tool_choice``. The model's reply contains a single
``tool_use`` block whose ``input`` we hand back to Pydantic for
validation.

The ``anthropic`` package is imported lazily inside ``__init__`` so the
rest of ``siphyy`` works without the ``[llm]`` extras installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from anthropic import Anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"
"""Balanced model. Override to ``claude-haiku-4-5-20251001`` for cheap/fast
runs or ``claude-opus-4-7`` for the hardest reasoning."""

DEFAULT_MAX_TOKENS = 4096


class AnthropicLLMClient:
    """LLMClient backed by Anthropic's Messages API + forced tool use."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: str | None = None,
        client: Anthropic | None = None,
    ) -> None:
        """
        Args:
            model: Anthropic model identifier.
            max_tokens: Output token cap.
            api_key: API key. Falls back to ``ANTHROPIC_API_KEY`` env var.
            client: Inject a pre-built ``anthropic.Anthropic`` instance.
                When provided, ``api_key`` is ignored.
        """
        if client is not None:
            self._client = client
        else:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete[T: BaseModel](
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        from anthropic.types import ToolUseBlock

        tool_name = f"respond_with_{response_model.__name__.lower()}"
        schema = response_model.model_json_schema()

        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Respond with a structured {response_model.__name__}.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )

        for block in response.content:
            if isinstance(block, ToolUseBlock) and block.name == tool_name:
                return response_model.model_validate(block.input)

        raise RuntimeError(
            f"Anthropic returned no tool_use block for {tool_name!r}. "
            f"Stop reason: {response.stop_reason!r}"
        )
