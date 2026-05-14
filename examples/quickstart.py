"""5-minute quickstart — schema -> adapter -> detector -> agent, end-to-end.

Run::

    uv run python examples/quickstart.py

What it does:
  1. Loads ``examples/data/sample_trakzee.json`` (anonymised synthetic data,
     designed to exercise both a real-siphonage scenario and a known
     slope-effect false positive).
  2. Translates rows into canonical ``TelemetryReading``s with
     ``TrakzeeAdapter``.
  3. Runs ``FuelSiphonageDetector`` (Tier 1) — surfaces the candidates.
  4. Runs ``FuelAnomalyAgent`` (Tier 2) — LLM-grounded interpretation.

The agent's LLM client is selected at runtime:
  * ``OPENAI_API_KEY`` in env  → uses ``OpenAILLMClient``
  * ``ANTHROPIC_API_KEY``      → uses ``AnthropicLLMClient``
  * Neither                    → uses ``MockLLMClient`` with realistic
                                  canned verdicts so the demo still works
                                  with zero setup

A ``.env`` at the repo root is honoured if ``python-dotenv`` is installed
(it's part of the ``[dev]`` extras).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Soft-load .env so API keys land in os.environ without a wrapper script.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from siphyy.adapters import TrakzeeAdapter
from siphyy.agents import (
    FuelAnomalyAgent,
    LLMClient,
    MockLLMClient,
)
from siphyy.agents.fuel_anomaly import _LLMVerdict
from siphyy.detectors import FuelSiphonageDetector
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase

SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "sample_trakzee.json"


def _pick_llm_client() -> tuple[LLMClient, str]:
    """Pick a real LLM if a key is available, else a mock with canned verdicts."""
    if os.getenv("OPENAI_API_KEY"):
        from siphyy.agents import OpenAILLMClient

        return OpenAILLMClient(model="gpt-4o-mini-2024-07-18"), "OpenAI (gpt-4o-mini)"
    if os.getenv("ANTHROPIC_API_KEY"):
        from siphyy.agents import AnthropicLLMClient

        return AnthropicLLMClient(model="claude-haiku-4-5-20251001"), "Anthropic (claude-haiku-4-5)"
    return MockLLMClient(_canned_verdicts()), "MockLLMClient (no API key in env)"


def _canned_verdicts() -> list[_LLMVerdict]:
    """Realistic verdicts that match the two scenarios baked into the sample
    data. Used when no API key is set so the demo still tells a complete story.
    Order matches the order events fire in the sample (vehicle-1 siphonage,
    vehicle-2 slope-effect false positive)."""
    siphonage = _LLMVerdict(
        assessment="likely_siphonage",
        confidence=0.92,
        summary="Active siphonage strongly suggested — pattern matches fuel_theft_0001.",
        reasoning=(
            "The drop magnitude (47%) and elapsed time (18 minutes) almost exactly "
            "match historical case fuel_theft_0001, which was confirmed siphonage via "
            "covert camera on a similar beverage truck. Engine off + ignition off rules "
            "out normal consumption. Thermal contraction (fuel_theft_0003) is implausible "
            "at this magnitude — that case attributed only ~14% over 22 minutes to a "
            "12°C cooling, an order of magnitude less than what we see here. The drop "
            "is far too rapid and too large to be sensor noise."
        ),
        recommended_actions=[
            "Investigate driver immediately",
            "Pull GPS history for the prior 6 hours and compare against planned route",
            "Inspect tank for unauthorized siphon valves",
            "Photograph current fuel level for evidentiary purposes",
        ],
        referenced_case_ids=["fuel_theft_0001", "fuel_theft_0003"],
    )
    slope_effect = _LLMVerdict(
        assessment="likely_false_positive",
        confidence=0.78,
        summary="Pattern matches post-climb fuel settling — likely sensor artifact, not theft.",
        reasoning=(
            "The 18% drop within 7 minutes of the vehicle coming to rest at altitude "
            "1335 m closely resembles the pattern documented in fuel_theft_0006 (a "
            "tanker with a longitudinal BLE probe parked at the top of a grade). That "
            "case identified the same signature: fuel re-distributes once engine "
            "vibration stops, dropping the apparent reading at the probe. The detector's "
            "altitude_delta is necessarily limited to the comparison pair, but the "
            "vehicle's high resting altitude is consistent with having just finished a "
            "climb. A manual dip-check should confirm before any action against the driver."
        ),
        recommended_actions=[
            "Request manual fuel dip-check before escalating",
            "Confirm vehicle route — was the vehicle climbing prior to parking?",
            "Enable Teltonika AVL IDs 256/257 on the FMB920 so future events carry "
            "explicit pitch data",
        ],
        referenced_case_ids=["fuel_theft_0006"],
    )
    return [siphonage, slope_effect]


def main() -> int:
    if not SAMPLE_PATH.exists():
        print(f"Sample data not found at {SAMPLE_PATH}", file=sys.stderr)
        return 1

    rows = json.loads(SAMPLE_PATH.read_text())
    print(f"Loaded {len(rows)} Trakzee-shaped rows from {SAMPLE_PATH.name}")

    llm_client, llm_label = _pick_llm_client()
    print(f"LLM client: {llm_label}")
    print()

    adapter = TrakzeeAdapter()
    detector = FuelSiphonageDetector()
    agent = FuelAnomalyAgent(llm_client=llm_client, case_base=CaseBase(SEED_CASES))

    events = list(adapter.adapt(rows))
    interesting = [ie for ev in events if (ie := detector.process(ev)) is not None]

    print(f"Canonical events:  {len(events)}")
    print(f"Tier 1 fires:      {len(interesting)}")
    print()

    for interesting_event in interesting:
        report = agent.process(interesting_event)
        if report is None:
            continue
        _print_report(report)

    return 0


def _print_report(report: object) -> None:
    """Pretty-print a FuelAnomalyReport so the demo output is scannable."""
    # Avoid importing the report type here — duck-typed access keeps this
    # function obvious to read.
    bar = "─" * 72
    print(bar)
    print(f"Vehicle:     {report.vehicle_id}")  # type: ignore[attr-defined]
    print(f"Detector:    {report.detector_name}")  # type: ignore[attr-defined]
    print(f"Verdict:     {report.assessment}  (confidence {report.confidence:.0%})")  # type: ignore[attr-defined]
    print(f"Summary:     {report.summary}")  # type: ignore[attr-defined]
    print()
    print("Reasoning:")
    for line in _wrap(report.reasoning, indent="  "):  # type: ignore[attr-defined]
        print(line)
    print()
    print("Recommended actions:")
    for action in report.recommended_actions:  # type: ignore[attr-defined]
        print(f"  • {action}")
    print()
    if report.referenced_case_ids:  # type: ignore[attr-defined]
        cited = ", ".join(report.referenced_case_ids)  # type: ignore[attr-defined]
        print(f"Cited cases: {cited}")
    print(bar)
    print()


def _wrap(text: str, width: int = 70, indent: str = "") -> list[str]:
    import textwrap

    return textwrap.wrap(text, width=width, initial_indent=indent, subsequent_indent=indent)


if __name__ == "__main__":
    raise SystemExit(main())
