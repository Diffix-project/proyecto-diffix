"""Tests del módulo app.agents.analyst.prompt (DIX-50).

Cubre:
- build_prompt incluye diff, competidor, rubro y sección.
- build_prompt define los 4 campos y los niveles de urgencia.
- Validación de industry y section.
"""

import pytest

from app.agents.analyst.prompt import URGENCY_LEVELS, build_prompt


class TestBuildPrompt:
    def test_includes_diff_competitor_industry_and_section(self):
        prompt = build_prompt(
            diff_text="- precio viejo: $100\n+ precio nuevo: $85",
            competitor_name="Competidor X",
            industry="food",
            section="pricing",
        )

        assert "Competidor X" in prompt
        assert "food" in prompt
        assert "pricing" in prompt
        assert "- precio viejo: $100" in prompt
        assert "+ precio nuevo: $85" in prompt

    def test_defines_four_required_fields(self):
        prompt = build_prompt(
            diff_text="cambio",
            competitor_name="Acme",
            industry="tech",
            section="home",
        )

        assert "what_changed" in prompt
        assert "why_it_matters" in prompt
        assert "what_to_do" in prompt
        assert "urgency" in prompt

    def test_defines_urgency_levels(self):
        prompt = build_prompt(
            diff_text="cambio",
            competitor_name="Acme",
            industry="construction",
            section="features",
        )

        for level in URGENCY_LEVELS:
            assert f'"{level}"' in prompt or level in prompt

    def test_urgency_examples_match_spec(self):
        """La guía de urgencia debe mencionar los ejemplos del spec."""
        prompt = build_prompt(
            diff_text="cambio",
            competitor_name="Acme",
            industry="other",
            section="general",
        )

        assert "precios" in prompt
        assert "nuevos productos" in prompt
        assert "expansiones" in prompt
        assert "contrataciones" in prompt
        assert "diseño" in prompt

    def test_requires_valid_industry(self):
        with pytest.raises(ValueError, match="industry inválido"):
            build_prompt(
                diff_text="cambio",
                competitor_name="Acme",
                industry="invalid_industry",
                section="pricing",
            )

    def test_requires_valid_section(self):
        with pytest.raises(ValueError, match="section inválida"):
            build_prompt(
                diff_text="cambio",
                competitor_name="Acme",
                industry="food",
                section="invalid_section",
            )

    def test_returns_string(self):
        prompt = build_prompt(
            diff_text="cambio",
            competitor_name="Acme",
            industry="tech",
            section="jobs",
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_asks_for_strict_json_only(self):
        prompt = build_prompt(
            diff_text="cambio",
            competitor_name="Acme",
            industry="food",
            section="pdf",
        )

        assert "solo" in prompt.lower()
        assert "JSON" in prompt
        # El ejemplo de JSON debe aparecer con llaves literales
        assert '{"what_changed": "..."' in prompt
