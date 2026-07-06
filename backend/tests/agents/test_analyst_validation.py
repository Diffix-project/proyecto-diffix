"""Tests del módulo app.agents.analyst.validation (DIX-51).

Cubre:
- Casos válidos.
- Campos faltantes o vacíos.
- Urgencia inválida.
- Tipos incorrectos.
"""

import pytest

from app.agents.analyst.validation import InvalidInsightError, validate_insight


class TestValidateInsight:
    def test_valid_insight_passes(self):
        data = {
            "what_changed": "Bajaron el precio del producto A.",
            "why_it_matters": "Afecta nuestra competitividad en el rubro.",
            "what_to_do": "Revisar márgenes y evaluar matching.",
            "urgency": "alta",
        }

        validate_insight(data)  # no debe lanzar

    @pytest.mark.parametrize("field", [
        "what_changed",
        "why_it_matters",
        "what_to_do",
        "urgency",
    ])
    def test_missing_field_raises(self, field):
        data = {
            "what_changed": "Bajaron el precio.",
            "why_it_matters": "Importante.",
            "what_to_do": "Actuar.",
            "urgency": "alta",
        }
        del data[field]

        with pytest.raises(InvalidInsightError, match=field):
            validate_insight(data)

    @pytest.mark.parametrize("field", [
        "what_changed",
        "why_it_matters",
        "what_to_do",
        "urgency",
    ])
    def test_empty_field_after_strip_raises(self, field):
        data = {
            "what_changed": "Bajaron el precio.",
            "why_it_matters": "Importante.",
            "what_to_do": "Actuar.",
            "urgency": "alta",
        }
        data[field] = "   "

        with pytest.raises(InvalidInsightError, match=field):
            validate_insight(data)

    @pytest.mark.parametrize("urgency", ["alta", "media", "baja"])
    def test_valid_urgency_values(self, urgency):
        data = {
            "what_changed": "X",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": urgency,
        }

        validate_insight(data)

    def test_invalid_urgency_raises(self):
        data = {
            "what_changed": "X",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "muy alta",
        }

        with pytest.raises(InvalidInsightError, match="urgency"):
            validate_insight(data)

    def test_urgency_is_case_insensitive(self):
        data = {
            "what_changed": "X",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "ALTA",
        }

        validate_insight(data)

    def test_non_string_field_raises(self):
        data = {
            "what_changed": 123,
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "alta",
        }

        with pytest.raises(InvalidInsightError, match="what_changed"):
            validate_insight(data)

    def test_non_dict_raises(self):
        with pytest.raises(InvalidInsightError, match="objeto JSON"):
            validate_insight(["not", "a", "dict"])

    def test_error_exposes_reason(self):
        data = {"urgency": "alta"}  # faltan campos

        with pytest.raises(InvalidInsightError) as exc_info:
            validate_insight(data)

        assert exc_info.value.reason
