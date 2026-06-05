"""Router del dominio billing."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_db_user
from app.core.plans import PLANES, PLANES_ORDENADOS
from app.core.security import verify_mp_webhook
from app.domains.auth.models import PLAN_VALUES, User
from app.domains.billing.schemas import (
    BillingCurrentOut,
    CheckoutIn,
    CheckoutOut,
    PlanOut,
)
from app.integrations import payments

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans() -> list[PlanOut]:
    """Lista todos los planes disponibles."""
    return [
        PlanOut(
            id=plan_id,
            nombre=plan.nombre,
            precio_usd=plan.precio_usd,
            limite_competidores=plan.limite_competidores,
            descripcion_alertas=plan.descripcion_alertas,
        )
        for plan_id in PLANES_ORDENADOS
        for plan in [PLANES[plan_id]]
    ]


@router.get("/current", response_model=BillingCurrentOut)
def get_current_billing(
    user: User = Depends(get_current_db_user),
) -> BillingCurrentOut:
    return BillingCurrentOut.model_validate(user)


@router.post("/checkout", response_model=CheckoutOut)
def create_checkout(
    data: CheckoutIn,
    user: User = Depends(get_current_db_user),
) -> CheckoutOut:
    if data.plan_id not in PLANES:
        raise HTTPException(status_code=400, detail=f"Plan inválido: {data.plan_id}")
    url = payments.create_checkout(data.plan_id, str(user.id))
    return CheckoutOut(url=url)


@router.post("/webhook", status_code=200)
async def mp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Webhook público de Mercado Pago. Actualiza el plan del usuario si el pago se aprueba."""
    payload = await request.body()
    headers = dict(request.headers)
    event = verify_mp_webhook(payload, headers)
    parsed = payments.parse_webhook(event)

    if parsed.get("status") != "approved":
        return {"received": True}

    clerk_id: str = parsed.get("user_clerk_id", "")
    plan: str = parsed.get("plan", "")

    if not clerk_id or plan not in PLAN_VALUES:
        logger.warning("billing webhook: datos inválidos clerk_id=%s plan=%s", clerk_id, plan)
        return {"received": True}

    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if user is None:
        logger.warning("billing webhook: usuario no encontrado clerk_id=%s", clerk_id)
        return {"received": True}

    user.plan = plan
    user.plan_expires_at = None  # Mercado Pago gestiona la vigencia externamente
    db.commit()
    logger.info("billing: plan actualizado clerk_id=%s → %s", clerk_id, plan)
    return {"received": True}
