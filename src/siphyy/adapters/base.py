"""Adapter base class.

Subclass this for each telematics provider. Adapters are the only place
provider-specific knowledge lives — field names, units, timestamp formats,
local timezones, JSON quirks, etc. Everything past `adapt()` is canonical.

A good adapter is:
  - Stateless (no shared mutable state between calls).
  - Side-effect free (no network calls, no DB writes — just data shaping).
  - Pure-functional in spirit — same input always produces same output.

Heavier integration concerns (rate-limiting, retries, dedup, persistence)
belong upstream of the adapter, not inside it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from siphyy.schema import CanonicalEvent


class TelematicsAdapter(ABC):
    """Translates one telematics provider's events into canonical events."""

    #: Short, lowercase provider identifier. Becomes `provider` on emitted events.
    name: str

    #: Schema version this adapter targets. Bumped when the canonical schema changes.
    schema_version: str = "1.0"

    @abstractmethod
    def adapt(self, raw: Iterable[object]) -> Iterable[CanonicalEvent]:
        """Translate a stream of provider-native records into canonical events.

        Adapters MAY:
          - Yield zero, one, or many canonical events per input record.
          - Skip records that don't carry useful information (return nothing).
          - Convert units, timezones, and synthesize event IDs.
          - Stash provider-specific fields in `provider_extras`.

        Adapters MUST NOT:
          - Fabricate values. Missing data stays None.
          - Make network calls. Adapters are pure transformations.
          - Modify input records (assume they may be reused upstream).
        """
        raise NotImplementedError
