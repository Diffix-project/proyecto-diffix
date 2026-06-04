"""
Dependencias compartidas entre dominios.

get_current_db_user: resuelve el User de la DB a partir del AuthUser de Clerk.
Si el usuario no existe (modo mock, primer acceso), lo crea on-demand.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import AuthUser, get_current_user
from app.domains.auth.models import User


def get_current_db_user(
    auth: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    from app.domains.auth.service import upsert_user_from_clerk  # noqa: PLC0415

    user = db.query(User).filter(User.clerk_id == auth.clerk_id).first()
    if user is None:
        # En modo mock creamos el usuario al vuelo
        user = upsert_user_from_clerk(db, auth.clerk_id, auth.email, auth.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user
