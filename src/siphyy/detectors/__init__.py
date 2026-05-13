"""Tier 1 detectors.

Detectors process canonical events and emit `InterestingEvent`s — events
worth handing to a Tier 2 LLM agent for interpretation. They are stateful
(they maintain per-vehicle rolling state) but cheap (no LLM calls, no
external API calls).

The fuel siphonage detector is the v0.1 reference implementation. More
to come.
"""

# TODO: Implement and re-export
# from siphyy.detectors.base import Detector, InterestingEvent
# from siphyy.detectors.fuel_siphonage import FuelSiphonageDetector

__all__: list[str] = []
