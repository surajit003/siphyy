"""Integration tests against real LLM providers.

Each test makes one small LLM call against a real provider's API.
Skipped automatically when the relevant API key isn't in env, so this
file is safe to commit and ship — it just does nothing in CI without
secrets configured. When running locally with a .env file at the repo
root, ``tests/conftest.py`` loads the keys before pytest collects.

Cost: one call per provider per run, against the cheapest model that
supports the structured-output mode each client uses. Total cost per
full run is on the order of a fraction of a cent.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from siphyy.agents import (
    AnthropicLLMClient,
    FuelAnomalyAgent,
    FuelAnomalyAssessment,
    OpenAILLMClient,
)
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase, InterestingEvent

_VALID_ASSESSMENTS = ("likely_siphonage", "likely_false_positive", "uncertain")


def _fuel_drop_event() -> InterestingEvent:
    """Realistic InterestingEvent matching the seed_case_0001 pattern."""
    return InterestingEvent(
        detector_name="fuel_siphonage",
        vehicle_id="trakzee:353201358420054",
        timestamp=datetime(2026, 5, 13, 2, 14, tzinfo=UTC),
        category="fuel_drop",
        severity="high",
        summary=(
            "Fuel sensor reading dropped 47% over 18 min while engine_state "
            "was stopped with ignition off."
        ),
        confidence=0.6,
        evidence={
            "drop_pct": 0.47,
            "prior_fuel_level_raw": 3597.0,
            "current_fuel_level_raw": 1906.0,
            "elapsed_minutes": 18.0,
            "engine_state": "stopped",
            "ignition_on": False,
            "fuel_sensor_type": "ble",
        },
        triggering_event_id="353201358420054:1747130918",
    )


def _assert_report_shape(report: object) -> None:
    """Validate the shape, not the specific verdict — LLMs are non-deterministic."""
    from siphyy.agents import FuelAnomalyReport

    assert isinstance(report, FuelAnomalyReport)
    assert report.assessment in _VALID_ASSESSMENTS
    assert 0.0 <= report.confidence <= 1.0
    assert report.summary.strip(), "summary must be non-empty"
    assert report.reasoning.strip(), "reasoning must be non-empty"
    assert report.vehicle_id == "trakzee:353201358420054"
    assert report.detector_name == "fuel_siphonage"


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
def test_openai_end_to_end() -> None:
    """Real OpenAI structured-output call producing a FuelAnomalyReport."""
    agent = FuelAnomalyAgent(
        llm_client=OpenAILLMClient(model="gpt-4o-mini-2024-07-18"),
        case_base=CaseBase(SEED_CASES),
    )
    report = agent.process(_fuel_drop_event())
    _assert_report_shape(report)


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_anthropic_end_to_end() -> None:
    """Real Anthropic tool-use call producing a FuelAnomalyReport."""
    agent = FuelAnomalyAgent(
        llm_client=AnthropicLLMClient(model="claude-haiku-4-5-20251001"),
        case_base=CaseBase(SEED_CASES),
    )
    report = agent.process(_fuel_drop_event())
    _assert_report_shape(report)


def _maybe_assessments() -> tuple[FuelAnomalyAssessment, ...]:
    """Type-narrow helper used in the assertion above."""
    return _VALID_ASSESSMENTS  # type: ignore[return-value]
