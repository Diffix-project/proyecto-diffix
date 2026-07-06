"""Tests de integración del paquete app.agents.analyst (DIX-54).

Cubre el flujo completo del core del Analyst con el LLM mockeado:
- generate_insight recibe un Change, construye el prompt, llama al LLM y valida.
- create_insight persiste el resultado con trazabilidad.
- Reintentos ante respuestas inválidas.
"""

from unittest.mock import patch

import pytest

from app.agents.analyst.core import AnalystError, generate_insight
from app.agents.analyst.persistence import create_insight
from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.insights.models import Insight
from app.domains.sources.models import CompetitorSource

VALID_INSIGHT = {
    "what_changed": "Bajaron el precio de lista del producto A.",
    "why_it_matters": "Nos deja 10% más caros en el principal SKU.",
    "what_to_do": "Revisar márgenes y evaluar matching esta semana.",
    "urgency": "alta",
}


class MockLLMResult:
    def __init__(
        self,
        data,
        model="gemini-mock",
        prompt_tokens=120,
        completion_tokens=80,
        trace_id="mock-trace-id",
    ):
        self.data = data
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.trace_id = trace_id


@pytest.fixture()
def sample_change(db, test_user):
    company = test_user.company
    competitor = Competitor(
        company_id=company.id,
        name="Competidor Integration",
        website_url="https://integration.com",
    )
    db.add(competitor)
    db.flush()

    source = CompetitorSource(
        competitor_id=competitor.id,
        source_type="website",
        source_url="https://integration.com",
        is_active=True,
    )
    db.add(source)
    db.flush()

    snapshot = Snapshot(
        competitor_id=competitor.id,
        source_id=source.id,
        source_type="website",
        content_hash="a" * 64,
        content="contenido actualizado",
    )
    db.add(snapshot)
    db.flush()

    change = Change(
        competitor_id=competitor.id,
        source_id=source.id,
        source_type="website",
        section="pricing",
        diff_text="- $100\n+ $85",
        diff_raw={"added": ["+ $85"], "removed": ["- $100"]},
        snapshot_after_id=snapshot.id,
        status="pending",
    )
    db.add(change)
    db.commit()
    return change


class TestAnalystCoreIntegration:
    @patch("app.agents.analyst.core.complete_json")
    def test_end_to_end_creates_insight(self, mock_complete, db, sample_change):
        mock_complete.return_value = MockLLMResult(VALID_INSIGHT)

        result = generate_insight(
            diff_text=sample_change.diff_text,
            competitor_name="Competidor Integration",
            industry="food",
            section="pricing",
        )

        insight = create_insight(db, sample_change, result)

        assert insight.change_id == sample_change.id
        assert insight.what_changed == VALID_INSIGHT["what_changed"]
        assert insight.urgency == "alta"
        assert insight.llm_model == "gemini-mock"
        assert insight.prompt_tokens == 120
        assert insight.completion_tokens == 80
        assert insight.langfuse_trace_id == "mock-trace-id"

        stored = db.get(Insight, insight.id)
        assert stored is not None

    @patch("app.agents.analyst.core.complete_json")
    def test_prompt_contains_diff_competitor_and_industry(self, mock_complete, sample_change):
        mock_complete.return_value = MockLLMResult(VALID_INSIGHT)

        generate_insight(
            diff_text=sample_change.diff_text,
            competitor_name="Competidor Integration",
            industry="food",
            section="pricing",
        )

        prompt = mock_complete.call_args[0][0]
        assert "- $100" in prompt
        assert "+ $85" in prompt
        assert "Competidor Integration" in prompt
        assert "food" in prompt
        assert "pricing" in prompt

    @patch("app.agents.analyst.core.complete_json")
    def test_retries_invalid_response_then_persists(self, mock_complete, db, sample_change):
        invalid = {
            "what_changed": "",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "alta",
        }
        mock_complete.side_effect = [
            MockLLMResult(invalid),
            MockLLMResult(VALID_INSIGHT),
        ]

        result = generate_insight(
            diff_text=sample_change.diff_text,
            competitor_name="Competidor Integration",
            industry="food",
            section="pricing",
        )

        insight = create_insight(db, sample_change, result)
        assert insight.urgency == "alta"
        assert mock_complete.call_count == 2

    @patch("app.agents.analyst.core.complete_json")
    def test_three_failures_do_not_create_insight(self, mock_complete, db, sample_change):
        invalid = {
            "what_changed": "",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "alta",
        }
        mock_complete.side_effect = [
            MockLLMResult(invalid),
            MockLLMResult(invalid),
            MockLLMResult(invalid),
        ]

        with pytest.raises(AnalystError):
            generate_insight(
                diff_text=sample_change.diff_text,
                competitor_name="Competidor Integration",
                industry="food",
                section="pricing",
            )

        assert mock_complete.call_count == 3
        assert db.query(Insight).filter(Insight.change_id == sample_change.id).first() is None
