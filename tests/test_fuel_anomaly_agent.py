"""Tests for FuelAnomalyAgent."""

from __future__ import annotations

from datetime import UTC, datetime

from siphyy.agents import FuelAnomalyAgent, FuelAnomalyReport, MockLLMClient
from siphyy.agents.fuel_anomaly import _LLMVerdict
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase, InterestingEvent


def _fuel_drop_event(
    *,
    category: str = "fuel_drop",
    severity: str = "high",
) -> InterestingEvent:
    return InterestingEvent(
        detector_name="fuel_siphonage",
        vehicle_id="trakzee:353201358420054",
        timestamp=datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
        category=category,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        summary="Fuel dropped 33% over 10 min while engine off.",
        confidence=0.6,
        evidence={
            "drop_pct": 0.33,
            "prior_fuel_level_raw": 3000.0,
            "current_fuel_level_raw": 2000.0,
            "engine_state": "stopped",
            "ignition_on": False,
        },
        triggering_event_id="353201358420054:1747130918",
    )


def _verdict(**overrides: object) -> _LLMVerdict:
    defaults: dict[str, object] = {
        "assessment": "likely_siphonage",
        "confidence": 0.8,
        "summary": "Pattern matches active siphonage.",
        "reasoning": "Drop magnitude and engine-off state match fuel_theft_0001.",
        "recommended_actions": ["Investigate driver", "Check vehicle GPS history"],
        "referenced_case_ids": ["fuel_theft_0001"],
    }
    defaults.update(overrides)
    return _LLMVerdict(**defaults)  # type: ignore[arg-type]


class TestFuelAnomalyAgent:
    def test_produces_report_for_fuel_drop_event(self) -> None:
        llm = MockLLMClient([_verdict()])
        agent = FuelAnomalyAgent(
            llm_client=llm,
            case_base=CaseBase(SEED_CASES),
            clock=lambda: datetime(2026, 5, 13, 10, 5, tzinfo=UTC),
        )

        report = agent.process(_fuel_drop_event())

        assert isinstance(report, FuelAnomalyReport)
        assert report.agent_name == "fuel_anomaly"
        assert report.assessment == "likely_siphonage"
        assert report.confidence == 0.8
        assert report.detector_name == "fuel_siphonage"
        assert report.vehicle_id == "trakzee:353201358420054"
        assert report.triggering_event_id == "353201358420054:1747130918"
        assert report.timestamp == datetime(2026, 5, 13, 10, 5, tzinfo=UTC)
        assert report.referenced_case_ids == ["fuel_theft_0001"]

    def test_declines_non_fuel_drop_categories(self) -> None:
        """Agent is purpose-built for fuel_drop. Other categories pass through."""
        llm = MockLLMClient([_verdict()])
        agent = FuelAnomalyAgent(llm_client=llm, case_base=CaseBase(SEED_CASES))

        # Force a non-matching category — using arg-type ignore since the
        # Literal currently only has one value but this future-proofs the test.
        event = _fuel_drop_event()
        event_dict = event.model_dump()
        event_dict["category"] = "harsh_event"
        # Build a model that bypasses the Literal check via construct().
        bypassed = InterestingEvent.model_construct(**event_dict)

        assert agent.process(bypassed) is None
        assert llm.calls == []  # never invoked

    def test_prompt_carries_event_details_and_cases(self) -> None:
        llm = MockLLMClient([_verdict()])
        agent = FuelAnomalyAgent(llm_client=llm, case_base=CaseBase(SEED_CASES))

        agent.process(_fuel_drop_event())

        assert len(llm.calls) == 1
        user_prompt = llm.calls[0]["user"]
        assert isinstance(user_prompt, str)
        assert "fuel_siphonage" in user_prompt
        assert "trakzee:353201358420054" in user_prompt
        assert "0.33" in user_prompt  # drop_pct from evidence
        # At least one historical case should be embedded in the prompt.
        assert "fuel_theft_0001" in user_prompt

    def test_max_cases_limits_retrieved_cases(self) -> None:
        llm = MockLLMClient([_verdict()])
        agent = FuelAnomalyAgent(
            llm_client=llm,
            case_base=CaseBase(SEED_CASES),
            max_cases=1,
        )

        agent.process(_fuel_drop_event())

        user_prompt = llm.calls[0]["user"]
        assert isinstance(user_prompt, str)
        # Exactly one case header line should appear when max_cases=1.
        header_count = user_prompt.count("Symptoms:")
        assert header_count == 1

    def test_handles_empty_case_base(self) -> None:
        """If the operator hasn't loaded any cases, the agent still runs —
        the LLM just gets a 'no historical cases' note."""
        llm = MockLLMClient([_verdict()])
        agent = FuelAnomalyAgent(llm_client=llm, case_base=CaseBase())

        report = agent.process(_fuel_drop_event())

        assert report is not None
        assert "no historical cases" in llm.calls[0]["user"]  # type: ignore[operator]

    def test_report_is_frozen(self) -> None:
        llm = MockLLMClient([_verdict()])
        agent = FuelAnomalyAgent(llm_client=llm, case_base=CaseBase(SEED_CASES))
        report = agent.process(_fuel_drop_event())

        assert report is not None
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            report.confidence = 0.1  # type: ignore[misc]
