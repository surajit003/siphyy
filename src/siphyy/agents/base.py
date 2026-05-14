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

import hashlib
import math
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

    Implementations also expose an ``embed`` method for similarity retrieval
    against the case base. Not every provider has a first-party embeddings
    API (Anthropic doesn't, as of writing); implementations are free to
    raise ``NotImplementedError`` from ``embed`` and the case base will
    gracefully fall back to category filtering.
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

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for ``text``.

        The dimensionality is provider-specific; the case base uses whatever
        the client returns and computes cosine similarity at retrieval time.
        Mixing clients with different embedding dimensions across index and
        retrieve will raise at retrieval — pick one and stick with it for a
        given case base.

        Implementations that don't have an embeddings endpoint should raise
        ``NotImplementedError`` with a clear message; the agent layer handles
        that case by falling back to category-only retrieval.
        """
        ...


class MockLLMClient:
    """LLMClient stand-in for tests.

    Construct with a sequence of pre-built response objects; the client
    returns them in order on each call to ``complete``. Use this to drive
    agent flow tests without touching a real LLM provider.

    ``embed`` returns a deterministic hash-based pseudo-embedding that
    preserves coarse semantic similarity (texts sharing tokens produce
    more similar vectors). Good enough for ordering-based tests; not a
    substitute for a real embedding model in production.
    """

    EMBED_DIM = 384

    def __init__(self, responses: list[BaseModel] | None = None) -> None:
        self._responses = list(responses) if responses is not None else []
        self._calls: list[dict[str, object]] = []
        self._embed_calls: list[str] = []

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

    def embed(self, text: str) -> list[float]:
        """Deterministic, semantically-coarse pseudo-embedding.

        Tokenises on whitespace (lowercased), hashes each token through
        SHA-256, and spreads it across the output dimensions. L2-normalised
        so cosine similarity is the natural distance. Two texts sharing
        many tokens produce vectors with high cosine similarity; unrelated
        texts cluster orthogonally.
        """
        self._embed_calls.append(text)
        vec = [0.0] * self.EMBED_DIM
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            for i in range(0, len(digest), 4):
                idx = int.from_bytes(digest[i : i + 4], "big") % self.EMBED_DIM
                vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    @property
    def calls(self) -> list[dict[str, object]]:
        """Recorded (system, user) prompts. Tests inspect this to verify
        the agent built the prompt it was supposed to."""
        return list(self._calls)

    @property
    def embed_calls(self) -> list[str]:
        """Recorded inputs to embed(). Useful for asserting that the agent
        actually requested embeddings for the expected texts."""
        return list(self._embed_calls)


class Agent[ReportT: BaseModel](ABC):
    """Tier 2 LLM agent.

    Subclasses override ``name`` and ``process``. ``process`` returns
    None when the agent declines to act on an event (wrong category,
    insufficient context, etc.).
    """

    name: str

    @abstractmethod
    def process(self, event: InterestingEvent) -> ReportT | None: ...
