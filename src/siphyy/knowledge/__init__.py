"""Knowledge layer — case bases, OEM manual indexes, fuel station registries.

This module ships the *interface*. The actual content (curated cases,
indexed manuals, station data) is shipped separately in the Siphyy
Knowledge Pack — and can also be self-curated by users for self-hosted
deployments.
"""

from siphyy.knowledge.seed_cases import SEED_CASES

__all__ = ["SEED_CASES"]
