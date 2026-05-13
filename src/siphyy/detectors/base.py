"""Detector base — the Tier 1 contract.

Detectors are cheap, deterministic, rule-based. They take a stream of
canonical events and emit a smaller stream of `InterestingEvent`s when
their rule fires. They do not call LLMs (that's Tier 2's job).

Detectors are stateful per-vehicle (e.g. "last seen fuel level for
vehicle V"). State is held in a `StateStore` so the same detector code
works against an in-memory dict in tests and Redis in production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from siphyy.schema import CanonicalEvent, InterestingEvent


class StateStore(Protocol):
    """Per-vehicle state storage.

    Detectors namespace their own keys (typically ``f"{detector_name}:{vehicle_id}"``)
    so multiple detectors can share one store without collision.
    """

    def get(self, key: str) -> dict[str, object] | None: ...

    def set(self, key: str, value: dict[str, object]) -> None: ...

    def delete(self, key: str) -> None: ...


class InMemoryStateStore:
    """Dict-backed StateStore. Fine for tests and single-process use; not
    safe across workers or process restarts. Production deployments should
    plug in a Redis-backed implementation against the same protocol.
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, object]] = {}

    def get(self, key: str) -> dict[str, object] | None:
        value = self._data.get(key)
        return dict(value) if value is not None else None

    def set(self, key: str, value: dict[str, object]) -> None:
        self._data[key] = dict(value)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


class Detector(ABC):
    """Tier 1 rule-based detector.

    Subclasses override ``name`` and ``process``. ``process`` is called
    once per canonical event in arrival order; state mutations between
    calls go through ``self.state``.
    """

    name: str

    def __init__(self, state_store: StateStore | None = None) -> None:
        self.state: StateStore = state_store if state_store is not None else InMemoryStateStore()

    @abstractmethod
    def process(self, event: CanonicalEvent) -> InterestingEvent | None:
        """Inspect one event. Return an InterestingEvent if a rule fires,
        else None. Implementations should be idempotent on irrelevant
        events (wrong type, missing data) — just return None.
        """

    def _state_key(self, vehicle_id: str) -> str:
        """Default keying scheme: ``"{detector_name}:{vehicle_id}"``."""
        return f"{self.name}:{vehicle_id}"
