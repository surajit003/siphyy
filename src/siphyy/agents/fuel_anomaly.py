"""Fuel anomaly agent — Tier 2 LLM interpretation of fuel-drop events.

Consumes an `InterestingEvent` from `FuelSiphonageDetector`, retrieves
relevant cases from the CaseBase (real siphonage and known
false-positive patterns), and asks the configured LLM to produce a
structured `FuelAnomalyReport`.

The LLM never sees provider-specific data — only canonical event fields
and case prose. The same agent works against any adapter's output.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from siphyy.agents.base import Agent, LLMClient
from siphyy.schema import CaseBase, IncidentCase, InterestingEvent

FuelAnomalyAssessment = Literal[
    "likely_siphonage",
    "likely_false_positive",
    "uncertain",
]
"""The agent's verdict on a fuel-drop event. Tier 2 is precision-oriented
— "uncertain" is a fine answer when the evidence doesn't justify a call."""


class _LLMVerdict(BaseModel):
    """Schema the LLM is asked to fill. Internal to this module."""

    model_config = ConfigDict(extra="forbid")

    assessment: FuelAnomalyAssessment
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(description="One-line plain-language verdict.")
    reasoning: str = Field(
        description="Longer explanation citing case IDs where relevant. "
        "Mention any contradictory evidence."
    )
    recommended_actions: list[str] = Field(default_factory=list)
    referenced_case_ids: list[str] = Field(default_factory=list)


class FuelAnomalyReport(BaseModel):
    """Structured output of `FuelAnomalyAgent`.

    Denormalised on purpose — reports are written-once, read-many, and
    storing the triggering event's identifiers inline avoids a join when
    a fleet manager views the report later.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    agent_name: str
    timestamp: datetime = Field(description="When the agent produced the report, in UTC.")

    # Traceability — which Tier 1 event drove this report.
    detector_name: str
    vehicle_id: str
    triggering_event_id: str | None

    # LLM-derived fields.
    assessment: FuelAnomalyAssessment
    confidence: float = Field(ge=0, le=1)
    summary: str
    reasoning: str
    recommended_actions: list[str] = Field(default_factory=list)
    referenced_case_ids: list[str] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You are a fleet analytics assistant specialised in fuel theft detection.

A Tier 1 rule-based detector has surfaced an event it considers
interesting. Your job is to assess whether it is likely real siphonage,
a likely false positive (thermal contraction, sensor drift, refuel
reversal, sensor noise), or genuinely uncertain — and to recommend
concrete action.

Ground your reasoning in the historical incident cases supplied. Cite
case IDs in your reasoning whenever a case informs your call. Prefer
"uncertain" over a confident wrong answer; false positives waste
investigator time and missed real siphonage costs money."""


class FuelAnomalyAgent(Agent[FuelAnomalyReport]):
    """Tier 2 agent for fuel-drop InterestingEvents."""

    name = "fuel_anomaly"

    def __init__(
        self,
        llm_client: LLMClient,
        case_base: CaseBase,
        *,
        max_cases: int = 5,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._llm = llm_client
        self._cases = case_base
        self._max_cases = max_cases
        self._clock = clock

    def process(self, event: InterestingEvent) -> FuelAnomalyReport | None:
        if event.category != "fuel_drop":
            return None

        relevant_cases = self._retrieve_cases()
        user_prompt = self._build_user_prompt(event, relevant_cases)

        verdict = self._llm.complete(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=_LLMVerdict,
        )

        return FuelAnomalyReport(
            agent_name=self.name,
            timestamp=self._clock(),
            detector_name=event.detector_name,
            vehicle_id=event.vehicle_id,
            triggering_event_id=event.triggering_event_id,
            assessment=verdict.assessment,
            confidence=verdict.confidence,
            summary=verdict.summary,
            reasoning=verdict.reasoning,
            recommended_actions=verdict.recommended_actions,
            referenced_case_ids=verdict.referenced_case_ids,
        )

    # ---- internals -------------------------------------------------

    def _retrieve_cases(self) -> list[IncidentCase]:
        """Cases worth showing the LLM. Pulls fuel-theft and false-positive
        precedents — true siphonage cases for pattern matching, false
        positives so the LLM can rule them out explicitly.

        Embedding-based similarity retrieval is a future upgrade; for now
        we hand over a small bounded set."""
        candidates = self._cases.filter(category="fuel_theft") + self._cases.filter(
            category="false_positive"
        )
        return candidates[: self._max_cases]

    def _build_user_prompt(self, event: InterestingEvent, cases: list[IncidentCase]) -> str:
        evidence_lines = [f"  {k}: {v}" for k, v in event.evidence.items()]
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "  (none)"

        case_blocks = (
            "\n\n".join(self._format_case(c) for c in cases)
            if cases
            else "(no historical cases available)"
        )

        return f"""\
A Tier 1 detector fired. Details below.

Detector: {event.detector_name}
Vehicle: {event.vehicle_id}
Timestamp (UTC): {event.timestamp.isoformat()}
Detector severity estimate: {event.severity}
Detector confidence estimate: {event.confidence}
Detector summary: {event.summary}

Evidence:
{evidence_block}

Relevant historical cases:

{case_blocks}

Assess this event."""

    @staticmethod
    def _format_case(case: IncidentCase) -> str:
        lessons = "\n".join(f"  - {lesson}" for lesson in case.lessons)
        return (
            f"[{case.case_id} | severity={case.severity} | region={case.region} | "
            f"vehicle_type={case.vehicle_type}]\n"
            f"Symptoms: {case.summary}\n"
            f"Diagnosis: {case.diagnosis}\n"
            f"Resolution: {case.resolution}\n"
            f"Lessons:\n{lessons}"
        )
