"""Schemas Pydantic para el dominio insights."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    change_id: uuid.UUID
    what_changed: str
    why_it_matters: str
    what_to_do: str
    urgency: str
    llm_model: str
    prompt_tokens: int
    completion_tokens: int
    langfuse_trace_id: str | None
    generated_at: datetime
