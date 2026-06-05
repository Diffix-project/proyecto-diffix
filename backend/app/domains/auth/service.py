"""Lógica de dominio para auth: upsert de usuario y resolución por clerk_id."""

import logging

from sqlalchemy.orm import Session

from app.domains.auth.models import Company, User

logger = logging.getLogger(__name__)


def get_user_by_clerk_id(db: Session, clerk_id: str) -> User | None:
    return db.query(User).filter(User.clerk_id == clerk_id).first()


def upsert_user_from_clerk(
    db: Session,
    clerk_id: str,
    email: str,
    name: str,
) -> User:
    """
    Crea o actualiza el User con el clerk_id dado.
    Si el User es nuevo, crea también su Company vacía para simplificar el
    scoping por company_id en el resto de los dominios.
    """
    user = get_user_by_clerk_id(db, clerk_id)
    if user is None:
        user = User(clerk_id=clerk_id, email=email, name=name or email)
        db.add(user)
        db.flush()  # necesitamos user.id para crear la Company
        company = Company(
            user_id=user.id,
            name="Mi empresa",
            industry="other",
        )
        db.add(company)
        logger.info("auth: nuevo usuario creado clerk_id=%s", clerk_id)
    else:
        user.email = email
        if name:
            user.name = name
        logger.info("auth: usuario actualizado clerk_id=%s", clerk_id)
    db.commit()
    db.refresh(user)
    return user
