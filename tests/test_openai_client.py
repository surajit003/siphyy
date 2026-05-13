"""Tests for OpenAILLMClient.

These tests don't hit the OpenAI API — they verify that the client
constructs the openai SDK call correctly given an injected stub. A
manually-runnable integration test (gated on OPENAI_API_KEY) would go
in a separate ``tests/integration/`` tree.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

# Skip everything in this file when openai isn't installed (the [llm] extra
# isn't present). The siphyy package itself must still import fine — the
# OpenAILLMClient module is import-safe; only construction touches openai.
pytest.importorskip("openai")

from siphyy.agents import OpenAILLMClient


class _Verdict(BaseModel):
    answer: str


def _stub_openai(parsed: BaseModel | None, refusal: str | None = None) -> tuple[Any, list[dict]]:
    """Build a minimal stand-in for openai.OpenAI() that records calls."""
    calls: list[dict] = []
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(parsed=parsed, refusal=refusal),
            )
        ],
    )

    def parse_fn(*, model: str, messages: list[dict], response_format: type) -> Any:
        calls.append({"model": model, "messages": messages, "response_format": response_format})
        return completion

    stub = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(parse=parse_fn),
            ),
        ),
    )
    return stub, calls


class TestOpenAILLMClient:
    def test_returns_parsed_pydantic_model(self) -> None:
        stub, _calls = _stub_openai(parsed=_Verdict(answer="yes"))
        client = OpenAILLMClient(client=stub, model="gpt-4o-2024-08-06")

        result = client.complete(system="s", user="u", response_model=_Verdict)

        assert isinstance(result, _Verdict)
        assert result.answer == "yes"

    def test_passes_model_and_messages_to_openai(self) -> None:
        stub, calls = _stub_openai(parsed=_Verdict(answer="ok"))
        client = OpenAILLMClient(client=stub, model="gpt-4.1")

        client.complete(system="SYS", user="USER", response_model=_Verdict)

        assert len(calls) == 1
        assert calls[0]["model"] == "gpt-4.1"
        assert calls[0]["messages"] == [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "USER"},
        ]
        assert calls[0]["response_format"] is _Verdict

    def test_raises_on_refusal(self) -> None:
        stub, _ = _stub_openai(parsed=None, refusal="I can't help with that.")
        client = OpenAILLMClient(client=stub)

        with pytest.raises(RuntimeError, match="Refusal"):
            client.complete(system="s", user="u", response_model=_Verdict)
