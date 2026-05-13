"""Interesting events — what Tier 1 detectors emit.

A Tier 1 detector takes a stream of canonical telemetry/driver events
and surfaces a much smaller stream of `InterestingEvent` payloads
when its rule fires. Tier 2 (the LLM agent) consumes these and decides
which ones warrant a structured incident report.

The schema is deliberately small. Detector-specific values (raw
sensor readings, baselines, thresholds crossed) live in `evidence`
rather than as first-class fields, so adding a new detector never
requires a schema change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from siphyy.schema.case import Severity

InterestingCategory = Literal["fuel_drop"]
"""What kind of rule fired. Grows as new detectors are added — additions are
non-breaking; renames or removals are breaking."""


class InterestingEvent(BaseModel):
    """A Tier 1 detector's notification that something warrants attention."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    detector_name: str = Field(description="The Detector.name that produced this event.")
    vehicle_id: str
    timestamp: datetime = Field(
        description="When the rule fired, in UTC. Usually the timestamp of the "
        "canonical event that triggered the firing."
    )
    category: InterestingCategory
    severity: Severity = Field(
        description="Detector's best guess at how serious the event is. Tier 2 "
        "may upgrade or downgrade this after retrieving relevant cases."
    )
    summary: str = Field(
        description="One-line human-readable explanation. The same prose register "
        "as IncidentCase.summary so that retrieval embeddings stay comparable."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Detector's confidence the rule fired correctly. Low confidence "
        "is fine — Tier 2 exists precisely to filter false positives.",
    )
    evidence: dict[str, object] = Field(
        default_factory=dict,
        description="Detector-specific values that explain the firing — raw sensor "
        "readings, thresholds crossed, baselines compared. Free-form by design.",
    )
    triggering_event_id: str | None = Field(
        default=None,
        description="provider_event_id of the canonical event that fired the rule, "
        "when one exists. Lets Tier 2 fetch the original telemetry row.",
    )
