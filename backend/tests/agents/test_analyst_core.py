"""Tests del módulo app.agents.analyst.core (DIX-52).

Cubre:
- generate_insight happy path.
- Reintentos ante validación fallida.
- Reintentos ante errores del LLM.
- Falla definitiva tras 3 intentos.
"""

from unittest.mock import patch

import pytest

from app.agents.analyst.core import AnalystError, AnalystResult, generate_insight

VALID_INSIGHT = {
    "what_changed": "Bajaron precios.",
    "why_it_matters": "Impacto competitivo.",
    "what_to_do": "Revisar márgenes.",
    "urgency": "alta",
}


class MockLLMResult:
    def __init__(
        self, data, model="test-model", prompt_tokens=10, completion_tokens=5, trace_id="trace-1"
    ):
        self.data = data
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.trace_id = trace_id


class TestGenerateInsight:
    @patch("app.agents.analyst.core.complete_json")
    def test_happy_path_returns_analyst_result(self, mock_complete):
        mock_complete.return_value = MockLLMResult(VALID_INSIGHT)

        result = generate_insight(
            diff_text="- $100\n+ $85",
            competitor_name="Competidor",
            industry="food",
            section="pricing",
        )

        assert isinstance(result, AnalystResult)
        assert result.insight == VALID_INSIGHT
        assert result.model == "test-model"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5
        assert result.trace_id == "trace-1"
        mock_complete.assert_called_once()

    @patch("app.agents.analyst.core.complete_json")
    def test_retries_on_invalid_response_and_succeeds_third_attempt(self, mock_complete):
        invalid = {"what_changed": "", "why_it_matters": "Y", "what_to_do": "Z", "urgency": "alta"}
        mock_complete.side_effect = [
            MockLLMResult(invalid),
            MockLLMResult(invalid),
            MockLLMResult(VALID_INSIGHT),
        ]

        result = generate_insight(
            diff_text="cambio",
            competitor_name="Competidor",
            industry="tech",
            section="home",
        )

        assert result.insight == VALID_INSIGHT
        assert mock_complete.call_count == 3

    @patch("app.agents.analyst.core.complete_json")
    def test_raises_after_three_failed_attempts(self, mock_complete):
        invalid = {"what_changed": "", "why_it_matters": "Y", "what_to_do": "Z", "urgency": "alta"}
        mock_complete.side_effect = [
            MockLLMResult(invalid),
            MockLLMResult(invalid),
            MockLLMResult(invalid),
        ]

        with pytest.raises(AnalystError, match="3 intentos"):
            generate_insight(
                diff_text="cambio",
                competitor_name="Competidor",
                industry="construction",
                section="features",
            )

        assert mock_complete.call_count == 3

    @patch("app.agents.analyst.core.complete_json")
    def test_retries_on_llm_error_and_succeeds(self, mock_complete):
        mock_complete.side_effect = [
            RuntimeError("timeout"),
            MockLLMResult(VALID_INSIGHT),
        ]

        result = generate_insight(
            diff_text="cambio",
            competitor_name="Competidor",
            industry="other",
            section="general",
        )

        assert result.insight == VALID_INSIGHT
        assert mock_complete.call_count == 2

    @patch("app.agents.analyst.core.complete_json")
    def test_raises_after_three_llm_errors(self, mock_complete):
        mock_complete.side_effect = RuntimeError("timeout")

        with pytest.raises(AnalystError):
            generate_insight(
                diff_text="cambio",
                competitor_name="Competidor",
                industry="food",
                section="jobs",
            )

        assert mock_complete.call_count == 3

    @patch("app.agents.analyst.core.complete_json")
    def test_passes_temperature(self, mock_complete):
        mock_complete.return_value = MockLLMResult(VALID_INSIGHT)

        generate_insight(
            diff_text="cambio",
            competitor_name="Competidor",
            industry="food",
            section="pdf",
        )

        _, kwargs = mock_complete.call_args
        assert kwargs["temperature"] == 0.3
