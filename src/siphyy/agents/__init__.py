"""Tier 2 LLM agents.

Agents take `InterestingEvent`s from Tier 1 detectors plus retrieved
context (cases from the CaseBase, OEM manuals) and produce structured
reports via an LLM with constrained output schemas.

Providers are pluggable: the `LLMClient` Protocol lets developers swap
OpenAI for Anthropic, Gemini, Ollama, or any OpenAI-compatible endpoint
without touching agent code.
"""

from siphyy.agents.anthropic_client import AnthropicLLMClient
from siphyy.agents.base import Agent, LLMClient, MockLLMClient
from siphyy.agents.fuel_anomaly import (
    FuelAnomalyAgent,
    FuelAnomalyAssessment,
    FuelAnomalyReport,
)
from siphyy.agents.openai_client import OpenAILLMClient

__all__ = [
    "Agent",
    "AnthropicLLMClient",
    "FuelAnomalyAgent",
    "FuelAnomalyAssessment",
    "FuelAnomalyReport",
    "LLMClient",
    "MockLLMClient",
    "OpenAILLMClient",
]
