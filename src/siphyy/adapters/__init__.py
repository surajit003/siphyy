"""Telematics provider adapters."""

from siphyy.adapters.base import TelematicsAdapter
from siphyy.adapters.samsara_stats import SamsaraStatsAdapter
from siphyy.adapters.samsara_webhook import SamsaraWebhookAdapter
from siphyy.adapters.trakzee import TrakzeeAdapter

__all__ = [
    "SamsaraStatsAdapter",
    "SamsaraWebhookAdapter",
    "TelematicsAdapter",
    "TrakzeeAdapter",
]
