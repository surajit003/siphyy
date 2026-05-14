"""Tests for vector-similarity retrieval on the case base.

Three responsibilities:

* MockLLMClient.embed produces deterministic vectors that preserve a
  coarse semantic similarity signal (shared tokens → higher cosine).
* CaseBase.index + CaseBase.retrieve rank cases by relevance to a query.
* CaseBase.retrieve falls back to category-only behaviour when the base
  hasn't been indexed yet — preserving the pre-vector behaviour.

The fixture is hand-picked so each query has an unambiguous expected
top match, even with the deliberately-naive token-overlap mock.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from siphyy.agents import MockLLMClient
from siphyy.schema import CaseBase, IncidentCase

# ──────────────────────────────────────────────────────────────────────
# Fixture: five cases with deliberately distinct vocabulary so the
# token-overlap mock embedder gives unambiguous rankings.
# ──────────────────────────────────────────────────────────────────────


def _make_case(case_id: str, summary: str, category: str = "fuel_theft") -> IncidentCase:
    return IncidentCase(
        case_id=case_id,
        category=category,  # type: ignore[arg-type]
        severity="medium",
        region="Zambia",
        vehicle_type="truck",
        summary=summary,
        diagnosis="...",
        resolution="...",
        lessons=["..."],
        tags=[],
        confidence=0.9,
        occurred_at=datetime(2026, 5, 13, 12, 0),
    )


@pytest.fixture
def fixture_cases() -> list[IncidentCase]:
    return [
        _make_case(
            "siphonage_overnight",
            "Fuel level dropped 47% overnight while engine off and parked at depot",
        ),
        _make_case(
            "thermal_contraction",
            "Fuel sensor reading shifted 14% due to thermal contraction overnight",
            category="false_positive",
        ),
        _make_case(
            "driver_detour",
            "Driver took unauthorized detour through Lusaka market town",
        ),
        _make_case(
            "tire_warning",
            "Tire pressure warning triggered during highway transit",
            category="vehicle_issue",
        ),
        _make_case(
            "offbook_refuel",
            "Refuel event recorded at coordinates outside known fuel stations",
        ),
    ]


# ──────────────────────────────────────────────────────────────────────
# Embedding round-trip
# ──────────────────────────────────────────────────────────────────────


class TestMockEmbedding:
    def test_deterministic(self) -> None:
        client = MockLLMClient()
        a = client.embed("fuel dropped overnight")
        b = client.embed("fuel dropped overnight")
        assert a == b

    def test_fixed_dimension(self) -> None:
        client = MockLLMClient()
        for text in ["short", "a longer text with several tokens", ""]:
            vec = client.embed(text)
            assert len(vec) == MockLLMClient.EMBED_DIM

    def test_l2_normalised(self) -> None:
        """Cosine similarity needs vectors of length 1 (or 0) to be honest."""
        import math

        client = MockLLMClient()
        vec = client.embed("fuel dropped overnight")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-9

    def test_empty_string_returns_zero_vector(self) -> None:
        client = MockLLMClient()
        vec = client.embed("")
        assert all(x == 0.0 for x in vec)

    def test_records_calls(self) -> None:
        client = MockLLMClient()
        client.embed("first")
        client.embed("second")
        assert client.embed_calls == ["first", "second"]


# ──────────────────────────────────────────────────────────────────────
# Indexing
# ──────────────────────────────────────────────────────────────────────


class TestCaseBaseIndex:
    def test_is_indexed_false_before_index_call(self, fixture_cases: list[IncidentCase]) -> None:
        base = CaseBase(fixture_cases)
        assert base.is_indexed is False

    def test_is_indexed_true_after_index(self, fixture_cases: list[IncidentCase]) -> None:
        base = CaseBase(fixture_cases)
        base.index(MockLLMClient())
        assert base.is_indexed is True

    def test_index_embeds_each_case_once(self, fixture_cases: list[IncidentCase]) -> None:
        client = MockLLMClient()
        base = CaseBase(fixture_cases)
        base.index(client)
        # Each case's summary should have been embedded exactly once.
        assert len(client.embed_calls) == len(fixture_cases)
        assert set(client.embed_calls) == {c.summary for c in fixture_cases}

    def test_index_is_idempotent(self, fixture_cases: list[IncidentCase]) -> None:
        """Re-running index() with the same embedder should not re-embed cases."""
        client = MockLLMClient()
        base = CaseBase(fixture_cases)
        base.index(client)
        calls_after_first = len(client.embed_calls)
        base.index(client)
        assert len(client.embed_calls) == calls_after_first

    def test_add_auto_embeds_after_index(self, fixture_cases: list[IncidentCase]) -> None:
        """Cases added after the first index call inherit the active embedder."""
        client = MockLLMClient()
        base = CaseBase(fixture_cases)
        base.index(client)
        new_case = _make_case("new", "Fresh case added after indexing")
        base.add(new_case)
        assert base.is_indexed is True  # still consistent
        # New case was embedded automatically (one extra call).
        assert client.embed_calls[-1] == new_case.summary


# ──────────────────────────────────────────────────────────────────────
# Retrieval — vector path
# ──────────────────────────────────────────────────────────────────────


class TestRetrievalBySimilarity:
    def test_siphonage_query_returns_siphonage_case_first(
        self, fixture_cases: list[IncidentCase]
    ) -> None:
        base = CaseBase(fixture_cases)
        base.index(MockLLMClient())
        results = base.retrieve("Fuel dropped while engine off", k=3)
        assert len(results) == 3
        assert results[0].case_id == "siphonage_overnight"

    def test_thermal_query_returns_thermal_case_first(
        self, fixture_cases: list[IncidentCase]
    ) -> None:
        base = CaseBase(fixture_cases)
        base.index(MockLLMClient())
        results = base.retrieve("Sensor reading thermal contraction overnight", k=3)
        assert results[0].case_id == "thermal_contraction"

    def test_detour_query_returns_detour_case_first(
        self, fixture_cases: list[IncidentCase]
    ) -> None:
        base = CaseBase(fixture_cases)
        base.index(MockLLMClient())
        results = base.retrieve("Driver detour unauthorized Lusaka", k=3)
        assert results[0].case_id == "driver_detour"

    def test_k_caps_result_count(self, fixture_cases: list[IncidentCase]) -> None:
        base = CaseBase(fixture_cases)
        base.index(MockLLMClient())
        assert len(base.retrieve("anything", k=1)) == 1
        assert len(base.retrieve("anything", k=2)) == 2
        # k > len(cases) is fine — we get back everything.
        assert len(base.retrieve("anything", k=999)) == len(fixture_cases)

    def test_category_filter_applied_after_ranking(self, fixture_cases: list[IncidentCase]) -> None:
        """Filtering by category narrows the candidate set; within that
        set, similarity ranking still applies."""
        base = CaseBase(fixture_cases)
        base.index(MockLLMClient())
        results = base.retrieve(
            "Fuel dropped while engine off",
            k=5,
            category="false_positive",  # type: ignore[arg-type]
        )
        # Only one false_positive case in the fixture — thermal_contraction.
        assert [c.case_id for c in results] == ["thermal_contraction"]


# ──────────────────────────────────────────────────────────────────────
# Retrieval — fallback path
# ──────────────────────────────────────────────────────────────────────


class TestRetrievalFallback:
    def test_returns_first_k_when_not_indexed(self, fixture_cases: list[IncidentCase]) -> None:
        """Without an index, retrieve returns the first k cases — the
        pre-vector behaviour."""
        base = CaseBase(fixture_cases)
        # No index() call.
        results = base.retrieve("anything", k=3)
        assert [c.case_id for c in results] == [
            "siphonage_overnight",
            "thermal_contraction",
            "driver_detour",
        ]

    def test_category_filter_works_when_not_indexed(
        self, fixture_cases: list[IncidentCase]
    ) -> None:
        base = CaseBase(fixture_cases)
        results = base.retrieve("anything", k=5, category="fuel_theft")  # type: ignore[arg-type]
        assert all(c.category == "fuel_theft" for c in results)
        # Three fuel_theft cases in the fixture.
        assert len(results) == 3

    def test_empty_base_returns_empty(self) -> None:
        base = CaseBase()
        base.index(MockLLMClient())  # no-op on empty
        assert base.retrieve("anything", k=3) == []

    def test_fallback_triggered_by_notimplementederror(
        self, fixture_cases: list[IncidentCase]
    ) -> None:
        """If the embedder doesn't support embeddings, index() raises and
        callers (the agent) are expected to catch it; subsequent retrieve()
        falls back to category-only behaviour."""

        class _NoEmbedClient:
            def embed(self, text: str) -> list[float]:
                raise NotImplementedError("no embeddings on this client")

        base = CaseBase(fixture_cases)
        with pytest.raises(NotImplementedError):
            base.index(_NoEmbedClient())
        # is_indexed stays False, retrieve falls back.
        assert base.is_indexed is False
        results = base.retrieve("anything", k=2)
        assert len(results) == 2
