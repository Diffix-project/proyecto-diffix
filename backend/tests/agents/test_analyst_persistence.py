"""Tests del módulo app.agents.analyst.persistence (DIX-53).

Cubre:
- create_insight persiste correctamente con trazabilidad.
- No permite duplicar insight para el mismo Change.
"""

import pytest
from sqlalchemy import select

from app.agents.analyst.persistence import create_insight
from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.insights.models import Insight
from app.domains.sources.models import CompetitorSource


class MockLLMResult:
    def __init__(
        self, data, model="test-model", prompt_tokens=10, completion_tokens=5, trace_id="trace-1"
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
        name="Competidor Test",
        website_url="https://test.com",
    )
    db.add(competitor)
    db.flush()

    source = CompetitorSource(
        competitor_id=competitor.id,
        source_type="website",
        source_url="https://test.com",
        is_active=True,
    )
    db.add(source)
    db.flush()

    snapshot = Snapshot(
        competitor_id=competitor.id,
        source_id=source.id,
        source_type="website",
        content_hash="a" * 64,
        content="nuevo contenido",
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


class TestCreateInsight:
    def test_creates_insight_with_all_fields(self, db, sample_change):
        data = {
            "what_changed": "Bajaron precios.",
            "why_it_matters": "Impacto competitivo.",
            "what_to_do": "Revisar márgenes.",
            "urgency": "alta",
        }
        llm_result = MockLLMResult(
            data, model="gemini-test", prompt_tokens=100, completion_tokens=50, trace_id="trace-abc"
        )

        insight = create_insight(db, sample_change, llm_result)

        assert insight.change_id == sample_change.id
        assert insight.what_changed == "Bajaron precios."
        assert insight.why_it_matters == "Impacto competitivo."
        assert insight.what_to_do == "Revisar márgenes."
        assert insight.urgency == "alta"
        assert insight.llm_model == "gemini-test"
        assert insight.prompt_tokens == 100
        assert insight.completion_tokens == 50
        assert insight.langfuse_trace_id == "trace-abc"

    def test_persists_insight(self, db, sample_change):
        data = {
            "what_changed": "X",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "media",
        }
        llm_result = MockLLMResult(data)

        create_insight(db, sample_change, llm_result)

        stored = db.scalar(select(Insight).where(Insight.change_id == sample_change.id))
        assert stored is not None
        assert stored.urgency == "media"

    def test_rejects_duplicate_insight_for_same_change(self, db, sample_change):
        data = {
            "what_changed": "X",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "baja",
        }
        llm_result = MockLLMResult(data)

        create_insight(db, sample_change, llm_result)

        with pytest.raises(ValueError, match="ya tiene un insight"):
            create_insight(db, sample_change, llm_result)

    def test_allows_null_trace_id(self, db, sample_change):
        data = {
            "what_changed": "X",
            "why_it_matters": "Y",
            "what_to_do": "Z",
            "urgency": "baja",
        }
        llm_result = MockLLMResult(data, trace_id=None)

        insight = create_insight(db, sample_change, llm_result)

        assert insight.langfuse_trace_id is None
