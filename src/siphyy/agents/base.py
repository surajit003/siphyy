"""Agent base — the Tier 2 contract.

Agents take an `InterestingEvent` from Tier 1 plus retrieved context
(cases from the CaseBase, OEM manuals once those land) and produce a
structured report via an LLM with a constrained output schema.

The `LLMClient` Protocol is the extension point: any provider —
OpenAI, Anthropic, Gemini, Ollama, a vLLM endpoint — can plug in by
implementing one method. Agents don't import provider SDKs directly,
so swapping providers never touches agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel

from siphyy.schema import InterestingEvent


class LLMClient(Protocol):
    """Adapter over an LLM provider.

    Implementations must return a validated instance of ``response_model``.
    How they get there (OpenAI structured outputs, Anthropic tool use,
    Gemini ``response_schema``, JSON-mode + Pydantic validation, ...) is
    provider-specific and not part of the contract.
    """

    def complete[T: BaseModel](
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        """Run a single LLM call and return a parsed instance of response_model."""
        ...


class MockLLMClient:
    """LLMClient stand-in for tests.

    Construct with a sequence of pre-built response objects; the client
    returns them in order on each call to ``complete``. Use this to drive
    agent flow tests without touching a real LLM provider.
    """

    def __init__(self, responses: list[BaseModel]) -> None:
        self._responses = list(responses)
        self._calls: list[dict[str, object]] = []

    def complete[T: BaseModel](
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        if not self._responses:
            raise RuntimeError("MockLLMClient ran out of canned responses.")
        response = self._responses.pop(0)
        if not isinstance(response, response_model):
            raise TypeError(
                f"MockLLMClient canned response is {type(response).__name__}, "
                f"agent asked for {response_model.__name__}."
            )
        self._calls.append({"system": system, "user": user})
        return response

    @property
    def calls(self) -> list[dict[str, object]]:
        """Recorded (system, user) prompts. Tests inspect this to verify
        the agent built the prompt it was supposed to."""
        return list(self._calls)


class Agent[ReportT: BaseModel](ABC):
    """Tier 2 LLM agent.

    Subclasses override ``name`` and ``process``. ``process`` returns
    None when the agent declines to act on an event (wrong category,
    insufficient context, etc.).
    """

    name: str

    @abstractmethod
    def process(self, event: InterestingEvent) -> ReportT | None: ...
