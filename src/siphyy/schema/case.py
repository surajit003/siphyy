"""Case Base schema — incidents that ground LLM reasoning via RAG.

A `Case` is one anonymised historical fleet incident with:
  - the symptoms (what the system saw),
  - the diagnosis (what was actually happening),
  - the resolution (what was done),
  - and the lessons / patterns to learn from.

Cases are retrieved at inference time by similarity to a current event's
symptoms, and pasted into the Tier 2 LLM prompt as grounded context.

The `summary` field is what gets embedded for similarity retrieval. The
full case body — diagnosis, resolution, lessons — is what's shown to the
LLM once a case has been retrieved.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

CaseCategory = Literal[
    "fuel_theft",
    "maintenance",
    "driver_behavior",
    "vehicle_issue",
    "route_anomaly",
    "false_positive",
]

Severity = Literal["critical", "high", "medium", "low"]


class IncidentCase(BaseModel):
    """One anonymised historical incident."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(description="Stable identifier, e.g. 'fuel_theft_0042'.")
    category: CaseCategory
    severity: Severity
    region: str = Field(description="Country or region — used for geo-relevance retrieval.")
    vehicle_type: str = Field(description="e.g. 'minitruck', 'beverage truck', 'tanker'.")

    summary: str = Field(
        description="Symptoms as the detection system observed them. THIS is what gets "
        "embedded for similarity retrieval. Write it in the same prose register "
        "as a Tier 1 detector's interesting-event payload."
    )
    diagnosis: str = Field(description="What was actually happening, established by investigation.")
    resolution: str = Field(
        description="Concrete action taken and the outcome (recovered fuel, "
        "driver dismissed, sensor calibrated, etc.)."
    )
    lessons: list[str] = Field(
        description="Generalisable patterns or rules. These are what make the case "
        "valuable beyond its specifics — the LLM uses them to reason about new events."
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags for filtering: 'night_event', 'off_route', etc.",
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="How certain the original diagnosis was. The LLM weighs "
        "high-confidence cases more heavily than ambiguous ones.",
    )
    occurred_at: datetime
    curated_at: datetime = Field(default_factory=datetime.now)


class Embedder(Protocol):
    """Minimum surface a case base needs from an LLM client.

    Defined locally so ``schema`` doesn't import from ``agents`` (which
    would create a circular dependency). Any object exposing
    ``embed(text) -> list[float]`` satisfies this — including
    :class:`~siphyy.agents.LLMClient` and its concrete implementations.
    """

    def embed(self, text: str) -> list[float]: ...


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two equal-length vectors.

    Returns 0.0 if either vector has zero magnitude; otherwise a value
    in roughly [-1, 1]. Pure Python — small vectors don't warrant numpy
    here, and keeping schema layer numpy-free preserves the ability to
    use the canonical types in lightweight contexts (CLI tools, edge
    devices) where pulling numpy would be heavyweight.
    """
    if len(a) != len(b):
        raise ValueError(
            f"Cosine similarity requires equal-length vectors; got {len(a)} vs {len(b)}. "
            "Make sure the same Embedder is used at index() and retrieve() time."
        )
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class CaseBase:
    """In-memory case base for development and small deployments.

    Two retrieval modes:

    * **Vector similarity** (preferred). Call :meth:`index` with an embedder
      once, then :meth:`retrieve` cosine-ranks against the stored vectors.
    * **Category filter fallback**. If the base hasn't been indexed (or the
      embedder is unavailable, e.g. AnthropicLLMClient raises
      ``NotImplementedError``), :meth:`retrieve` falls back to category-only
      filtering plus a slice — the pre-vector behaviour.

    Production deployments back this with pgvector — same public interface,
    swap the storage layer. See siphyy.knowledge.pgvector_store (planned).
    """

    def __init__(self, cases: list[IncidentCase] | None = None) -> None:
        self.cases: list[IncidentCase] = list(cases) if cases else []
        self._embeddings: dict[str, list[float]] = {}
        self._embedder: Embedder | None = None

    # ─── Indexing ────────────────────────────────────────────────────

    @property
    def is_indexed(self) -> bool:
        """True iff every case has a cached embedding and a query embedder
        is available. Drives the vector-vs-fallback path in :meth:`retrieve`."""
        return (
            self._embedder is not None
            and bool(self.cases)
            and len(self._embeddings) == len(self.cases)
        )

    def index(self, embedder: Embedder) -> None:
        """Compute and cache an embedding for every case's ``summary`` field.

        Idempotent — re-running is cheap (only the missing cases get
        embedded). The embedder is also stored so :meth:`retrieve` can embed
        query strings against the same vector space.

        If the embedder raises ``NotImplementedError`` (e.g. Anthropic has no
        first-party embeddings endpoint), the exception propagates — callers
        should handle it and let :meth:`retrieve` fall back gracefully.
        """
        for case in self.cases:
            if case.case_id not in self._embeddings:
                self._embeddings[case.case_id] = embedder.embed(case.summary)
        self._embedder = embedder

    # ─── Retrieval ───────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        *,
        k: int = 3,
        category: CaseCategory | None = None,
    ) -> list[IncidentCase]:
        """Return up to ``k`` cases most relevant to ``query``.

        When the base is indexed, ranking is by cosine similarity between
        the query's embedding and each case's stored embedding. When the
        base is not indexed, falls back to category-only filtering — the
        original pre-vector behaviour, so callers built before indexing
        existed continue to work.

        Args:
            query: free-text to match against case summaries.
            k: maximum number of cases to return.
            category: optional filter, applied after similarity ranking
                (or as the sole filter in fallback mode).
        """
        if self.is_indexed:
            return self._retrieve_by_similarity(query=query, k=k, category=category)
        return self._retrieve_by_category(category=category, k=k)

    def _retrieve_by_similarity(
        self,
        *,
        query: str,
        k: int,
        category: CaseCategory | None,
    ) -> list[IncidentCase]:
        # mypy-narrow: is_indexed guarantees _embedder is not None.
        assert self._embedder is not None
        query_vec = self._embedder.embed(query)
        scored: list[tuple[IncidentCase, float]] = []
        for case in self.cases:
            if category is not None and case.category != category:
                continue
            case_vec = self._embeddings.get(case.case_id)
            if case_vec is None:
                continue
            scored.append((case, _cosine_similarity(query_vec, case_vec)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [case for case, _ in scored[:k]]

    def _retrieve_by_category(
        self,
        *,
        category: CaseCategory | None,
        k: int,
    ) -> list[IncidentCase]:
        candidates = self.cases if category is None else self.filter(category=category)
        return candidates[:k]

    # ─── Existing surface (unchanged) ────────────────────────────────

    def add(self, case: IncidentCase, embedding: list[float] | None = None) -> None:
        self.cases.append(case)
        if embedding is not None:
            self._embeddings[case.case_id] = embedding
        elif self._embedder is not None:
            # Auto-embed: the base was previously indexed, so keep it
            # consistent without forcing the caller to re-call index().
            self._embeddings[case.case_id] = self._embedder.embed(case.summary)

    def get(self, case_id: str) -> IncidentCase | None:
        return next((c for c in self.cases if c.case_id == case_id), None)

    def filter(
        self,
        *,
        category: CaseCategory | None = None,
        region: str | None = None,
    ) -> list[IncidentCase]:
        result = self.cases
        if category is not None:
            result = [c for c in result if c.category == category]
        if region is not None:
            result = [c for c in result if c.region == region]
        return result

    def to_jsonl(self) -> str:
        """Serialise to JSONL — the canonical Knowledge Pack distribution format."""
        return "\n".join(c.model_dump_json() for c in self.cases)

    def __len__(self) -> int:
        return len(self.cases)
