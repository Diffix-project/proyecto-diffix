"""Persistencia del Insight generado por el Analyst Agent.

Expone:
  create_insight(db, change, llm_result): crea y persiste un Insight vinculado a un Change.
"""

import logging
from typing import Protocol

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.domains.changes.models import Change
from app.domains.insights.models import Insight

logger = logging.getLogger(__name__)


class _LLMResultLike(Protocol):
    """Interfaz mínima que debe cumplir `llm_result` para persistir."""

    data: dict
    model: str
    prompt_tokens: int
    completion_tokens: int
    trace_id: str | None


def create_insight(db: Session, change: Change, llm_result: _LLMResultLike) -> Insight:
    """
    Crea y persiste un Insight a partir de un Change y el resultado del LLM.

    Args:
        db: Sesión de SQLAlchemy.
        change: Change para el cual se generó el insight.
        llm_result: Resultado de la llamada al LLM (o AnalystResult), con los
            campos data, model, prompt_tokens, completion_tokens y trace_id.

    Returns:
        El Insight persistido.

    Raises:
        ValueError: Si el Change ya tiene un Insight asociado.
    """
    existing = db.scalar(
        sa.select(Insight).where(Insight.change_id == change.id).limit(1)
    )
    if existing is not None:
        raise ValueError(f"El change {change.id} ya tiene un insight asociado")

    insight = Insight(
        change_id=change.id,
        what_changed=llm_result.data["what_changed"].strip(),
        why_it_matters=llm_result.data["why_it_matters"].strip(),
        what_to_do=llm_result.data["what_to_do"].strip(),
        urgency=llm_result.data["urgency"].strip().lower(),
        llm_model=llm_result.model,
        prompt_tokens=llm_result.prompt_tokens,
        completion_tokens=llm_result.completion_tokens,
        langfuse_trace_id=llm_result.trace_id,
    )
    db.add(insight)
    db.flush()
    logger.info("create_insight: insight creado id=%s para change_id=%s", insight.id, change.id)
    return insight
