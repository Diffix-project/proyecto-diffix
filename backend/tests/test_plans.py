"""
Tests unitarios para app.core.plans.

Verifican:
- competitor_limit devuelve el límite correcto para cada plan.
- is_within_limit respeta el límite y el caso ilimitado (business).
"""

import pytest

from app.core.plans import competitor_limit, is_within_limit


class TestCompetitorLimit:
    def test_free_limit(self):
        assert competitor_limit("free") == 2

    def test_starter_limit(self):
        assert competitor_limit("starter") == 5

    def test_growth_limit(self):
        assert competitor_limit("growth") == 10

    def test_business_unlimited(self):
        assert competitor_limit("business") is None

    def test_unknown_plan_raises(self):
        with pytest.raises(KeyError):
            competitor_limit("enterprise")


class TestIsWithinLimit:
    def test_free_under_limit(self):
        assert is_within_limit("free", 0) is True
        assert is_within_limit("free", 1) is True

    def test_free_at_limit(self):
        assert is_within_limit("free", 2) is False

    def test_free_over_limit(self):
        assert is_within_limit("free", 5) is False

    def test_starter_under_limit(self):
        assert is_within_limit("starter", 4) is True

    def test_starter_at_limit(self):
        assert is_within_limit("starter", 5) is False

    def test_growth_under_limit(self):
        assert is_within_limit("growth", 9) is True

    def test_growth_at_limit(self):
        assert is_within_limit("growth", 10) is False

    def test_business_always_within_limit(self):
        assert is_within_limit("business", 0) is True
        assert is_within_limit("business", 100) is True
        assert is_within_limit("business", 9999) is True
