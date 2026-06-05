"""Router del dominio auth."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import AuthUser, get_current_user, verify_clerk_webhook
from app.domains.auth.schemas import UserOut
from app.domains.auth.service import get_user_by_clerk_id, upsert_user_from_clerk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/webhook", status_code=200)
async def clerk_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Webhook público de Clerk. Upsert de usuario en user.created / user.updated."""
    payload = await request.body()
    headers = dict(request.headers)
    event = verify_clerk_webhook(payload, headers)

    event_type: str = event.get("type", "")
    if event_type not in ("user.created", "user.updated"):
        return {"received": True}

    data = event.get("data", {})
    clerk_id: str = data.get("id", "")
    email_addresses: list = data.get("email_addresses", [])
    email: str = ""
    if email_addresses:
        email = email_addresses[0].get("email_address", "")

    first_name: str = data.get("first_name") or ""
    last_name: str = data.get("last_name") or ""
    name = f"{first_name} {last_name}".strip() or email

    if not clerk_id:
        raise HTTPException(status_code=400, detail="Payload inválido: falta id")

    upsert_user_from_clerk(db, clerk_id=clerk_id, email=email, name=name)
    return {"received": True}


@router.get("/me", response_model=UserOut)
async def get_me(
    auth: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """Retorna el usuario autenticado con su empresa y plan."""
    user = get_user_by_clerk_id(db, auth.clerk_id)
    if user is None:
        # En modo mock creamos el usuario al vuelo si no existe
        from app.domains.auth.service import upsert_user_from_clerk  # noqa: PLC0415

        user = upsert_user_from_clerk(db, auth.clerk_id, auth.email, auth.email)
    return UserOut.model_validate(user)
