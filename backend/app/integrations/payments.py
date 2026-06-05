"""
Integración con Mercado Pago.

Interfaz pública:
  create_checkout(plan_id, user_id) -> str          URL de checkout
  parse_webhook(payload) -> dict                     evento normalizado

En modo mock no realiza ninguna llamada de red.
En modo real usa la API de Mercado Pago (stub para fase Billing).
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_checkout(plan_id: str, user_id: str) -> str:
    """
    Crea una preferencia de pago en Mercado Pago y devuelve la URL de checkout.

    Mock: devuelve URL falsa sin llamada de red.
    Real: TODO — implementar en fase Billing con la API de Mercado Pago.
    """
    if settings.use_mocks:
        logger.debug("payments [mock] create_checkout plan=%s user=%s", plan_id, user_id)
        return f"https://mock.mercadopago/checkout/{plan_id}?user={user_id}"

    # Real: fase Billing
    raise NotImplementedError("payments real mode: completar en fase Billing")


def parse_webhook(payload: dict) -> dict:
    """
    Normaliza el payload de un webhook de Mercado Pago.

    Devuelve dict con claves: plan, user_clerk_id, status.

    Mock: passthrough simple que extrae los campos si existen.
    Real: TODO — implementar verificación de firma + normalización en fase Billing.
    """
    if settings.use_mocks:
        logger.debug("payments [mock] parse_webhook payload=%s", payload)
        return {
            "plan": payload.get("plan", "starter"),
            "user_clerk_id": payload.get("user_clerk_id", ""),
            "status": payload.get("status", "approved"),
        }

    # Real: fase Billing
    raise NotImplementedError("payments real mode: completar en fase Billing")
