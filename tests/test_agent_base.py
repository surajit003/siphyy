"""Tests for the agent base + MockLLMClient."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from siphyy.agents import MockLLMClient


class _Verdict(BaseModel):
    answer: str


class _OtherModel(BaseModel):
    something: int


class TestMockLLMClient:
    def test_returns_canned_responses_in_order(self) -> None:
        client = MockLLMClient([_Verdict(answer="first"), _Verdict(answer="second")])

        first = client.complete(system="s", user="u", response_model=_Verdict)
        second = client.complete(system="s", user="u", response_model=_Verdict)

        assert first.answer == "first"
        assert second.answer == "second"

    def test_records_prompts_for_inspection(self) -> None:
        client = MockLLMClient([_Verdict(answer="x")])
        client.complete(system="sys-prompt", user="user-prompt", response_model=_Verdict)

        assert client.calls == [{"system": "sys-prompt", "user": "user-prompt"}]

    def test_raises_when_canned_responses_exhausted(self) -> None:
        client = MockLLMClient([])
        with pytest.raises(RuntimeError, match="ran out"):
            client.complete(system="s", user="u", response_model=_Verdict)

    def test_raises_on_response_model_mismatch(self) -> None:
        """If the agent asks for type A but the test set up type B, fail loudly
        so the test doesn't silently pass with the wrong shape."""
        client = MockLLMClient([_Verdict(answer="x")])
        with pytest.raises(TypeError, match="agent asked for"):
            client.complete(system="s", user="u", response_model=_OtherModel)
