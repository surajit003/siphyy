"""Tests for AnthropicLLMClient.

Stubs the anthropic SDK rather than hitting the real API. Integration
tests against the real Messages endpoint live in ``tests/integration/``
and only run when ANTHROPIC_API_KEY is set.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

pytest.importorskip("anthropic")

from anthropic.types import ToolUseBlock

from siphyy.agents import AnthropicLLMClient


class _Verdict(BaseModel):
    answer: str


def _stub_anthropic(
    tool_input: dict | None,
    *,
    tool_name: str = "respond_with__verdict",
    stop_reason: str = "tool_use",
) -> tuple[Any, list[dict]]:
    """Minimal stand-in for anthropic.Anthropic() that records calls."""
    calls: list[dict] = []
    content: list[Any]
    if tool_input is not None:
        content = [
            ToolUseBlock(
                id="tu_test",
                name=tool_name,
                input=tool_input,
                type="tool_use",
            ),
        ]
    else:
        content = []
    response = SimpleNamespace(content=content, stop_reason=stop_reason)

    def create_fn(
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_choice: dict,
    ) -> Any:
        calls.append(
            {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        return response

    stub = SimpleNamespace(messages=SimpleNamespace(create=create_fn))
    return stub, calls


class TestAnthropicLLMClient:
    def test_returns_parsed_pydantic_model(self) -> None:
        stub, _ = _stub_anthropic({"answer": "yes"})
        client = AnthropicLLMClient(client=stub)

        result = client.complete(system="s", user="u", response_model=_Verdict)

        assert isinstance(result, _Verdict)
        assert result.answer == "yes"

    def test_forces_tool_use_with_response_model_schema(self) -> None:
        stub, calls = _stub_anthropic({"answer": "ok"})
        client = AnthropicLLMClient(client=stub, model="claude-haiku-4-5-20251001")

        client.complete(system="SYS", user="USER", response_model=_Verdict)

        assert len(calls) == 1
        call = calls[0]
        assert call["model"] == "claude-haiku-4-5-20251001"
        assert call["system"] == "SYS"
        assert call["messages"] == [{"role": "user", "content": "USER"}]

        # One forced tool whose schema is _Verdict's JSON schema.
        assert len(call["tools"]) == 1
        tool = call["tools"][0]
        assert tool["name"] == "respond_with__verdict"
        assert tool["input_schema"] == _Verdict.model_json_schema()
        assert call["tool_choice"] == {"type": "tool", "name": "respond_with__verdict"}

    def test_raises_when_no_tool_use_block(self) -> None:
        """Anthropic occasionally returns no tool_use (refusal, max_tokens hit
        mid-call, etc). We surface that as a RuntimeError so callers don't
        silently get a malformed result."""
        stub, _ = _stub_anthropic(None, stop_reason="end_turn")
        client = AnthropicLLMClient(client=stub)

        with pytest.raises(RuntimeError, match="no tool_use block"):
            client.complete(system="s", user="u", response_model=_Verdict)
