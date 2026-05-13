"""Tier 1 detectors.

Detectors process canonical events and emit `InterestingEvent`s — events
worth handing to a Tier 2 LLM agent for interpretation. They are stateful
(per-vehicle rolling state via a `StateStore`) but cheap: no LLM calls,
no external API calls.

The fuel siphonage detector is the v0.1 reference implementation.
"""

from siphyy.detectors.base import Detector, InMemoryStateStore, StateStore
from siphyy.detectors.fuel_siphonage import FuelSiphonageDetector

__all__ = [
    "Detector",
    "FuelSiphonageDetector",
    "InMemoryStateStore",
    "StateStore",
]
