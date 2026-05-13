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

from datetime import datetime
from typing import Literal

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


class CaseBase:
    """In-memory case base for development and small deployments.

    Production deployments back this with pgvector — same interface, swap
    the storage layer. See siphyy.knowledge.pgvector_store (planned).
    """

    def __init__(self, cases: list[IncidentCase] | None = None) -> None:
        self.cases: list[IncidentCase] = list(cases) if cases else []
        self._embeddings: dict[str, list[float]] = {}

    def add(self, case: IncidentCase, embedding: list[float] | None = None) -> None:
        self.cases.append(case)
        if embedding is not None:
            self._embeddings[case.case_id] = embedding

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
