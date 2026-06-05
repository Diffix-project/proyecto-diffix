"""Schemas Pydantic para el dominio billing."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlanOut(BaseModel):
    id: str
    nombre: str
    precio_usd: int
    limite_competidores: int | None
    descripcion_alertas: str


class BillingCurrentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: str
    plan_expires_at: datetime | None


class CheckoutIn(BaseModel):
    plan_id: str


class CheckoutOut(BaseModel):
    url: str
