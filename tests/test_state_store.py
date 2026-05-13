"""Tests for the in-memory state store."""

from __future__ import annotations

from siphyy.detectors import InMemoryStateStore


class TestInMemoryStateStore:
    def test_empty_get_returns_none(self) -> None:
        store = InMemoryStateStore()
        assert store.get("missing") is None

    def test_set_and_get_round_trip(self) -> None:
        store = InMemoryStateStore()
        store.set("v1", {"fuel_level_raw": 3597.0, "timestamp": "2026-05-13T10:00:00+00:00"})
        assert store.get("v1") == {
            "fuel_level_raw": 3597.0,
            "timestamp": "2026-05-13T10:00:00+00:00",
        }

    def test_set_overwrites(self) -> None:
        store = InMemoryStateStore()
        store.set("v1", {"x": 1})
        store.set("v1", {"x": 2})
        assert store.get("v1") == {"x": 2}

    def test_delete(self) -> None:
        store = InMemoryStateStore()
        store.set("v1", {"x": 1})
        store.delete("v1")
        assert store.get("v1") is None

    def test_delete_missing_is_a_noop(self) -> None:
        store = InMemoryStateStore()
        store.delete("never_set")  # must not raise

    def test_get_returns_independent_copy(self) -> None:
        """Mutating the dict that `get` returned must not change the stored value."""
        store = InMemoryStateStore()
        store.set("v1", {"x": 1})
        returned = store.get("v1")
        assert returned is not None
        returned["x"] = 999
        assert store.get("v1") == {"x": 1}

    def test_set_takes_independent_copy(self) -> None:
        """Mutating the dict that was passed to `set` must not change the stored value."""
        store = InMemoryStateStore()
        state = {"x": 1}
        store.set("v1", state)
        state["x"] = 999
        assert store.get("v1") == {"x": 1}
