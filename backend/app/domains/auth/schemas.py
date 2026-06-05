"""Schemas Pydantic para el dominio auth."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str
    country: str
    created_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_id: str
    email: str
    name: str
    plan: str
    plan_expires_at: datetime | None
    company: CompanyOut | None
    created_at: datetime
    updated_at: datetime
