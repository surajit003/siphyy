"""Tests for the Knowledge Pack case base."""

from __future__ import annotations

from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase, IncidentCase


class TestSeedCases:
    def test_loads(self) -> None:
        assert len(SEED_CASES) >= 5

    def test_case_diversity(self) -> None:
        """Seed cases should span categories — including a false positive."""
        categories = {c.category for c in SEED_CASES}
        assert "fuel_theft" in categories
        assert "false_positive" in categories

    def test_case_regions_diverse(self) -> None:
        regions = {c.region for c in SEED_CASES}
        assert len(regions) >= 3

    def test_every_case_has_lessons(self) -> None:
        for case in SEED_CASES:
            assert len(case.lessons) >= 1, f"{case.case_id} has no lessons"


class TestCaseBase:
    def test_empty_init(self) -> None:
        base = CaseBase()
        assert len(base) == 0

    def test_init_with_cases(self) -> None:
        base = CaseBase(SEED_CASES)
        assert len(base) == len(SEED_CASES)

    def test_filter_by_category(self) -> None:
        base = CaseBase(SEED_CASES)
        theft = base.filter(category="fuel_theft")
        assert all(c.category == "fuel_theft" for c in theft)

    def test_filter_by_region(self) -> None:
        base = CaseBase(SEED_CASES)
        zambia = base.filter(region="Zambia")
        assert all(c.region == "Zambia" for c in zambia)

    def test_get_by_id(self) -> None:
        base = CaseBase(SEED_CASES)
        case = base.get("fuel_theft_0001")
        assert case is not None
        assert case.case_id == "fuel_theft_0001"

    def test_get_missing_returns_none(self) -> None:
        base = CaseBase(SEED_CASES)
        assert base.get("nonexistent") is None

    def test_jsonl_round_trip(self) -> None:
        base = CaseBase(SEED_CASES)
        jsonl = base.to_jsonl()
        lines = jsonl.strip().split("\n")
        assert len(lines) == len(SEED_CASES)
        # Each line should parse back into an IncidentCase
        for line in lines:
            case = IncidentCase.model_validate_json(line)
            assert case.case_id.startswith(("fuel_theft", "maintenance"))
