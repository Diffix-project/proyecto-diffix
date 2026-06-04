"""Lógica de dominio para competitors."""

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import PlanLimitReached
from app.core.plans import is_within_limit
from app.domains.auth.models import Company, User
from app.domains.competitors.models import Competitor
from app.domains.competitors.schemas import CompetitorCreate, CompetitorUpdate, SourceIn
from app.domains.sources.models import CompetitorSource

logger = logging.getLogger(__name__)


def _get_company(db: Session, user: User) -> Company:
    if user.company is None:
        raise HTTPException(
            status_code=400,
            detail="El usuario no tiene empresa configurada.",
        )
    return user.company


def _get_competitor_for_user(db: Session, competitor_id: uuid.UUID, user: User) -> Competitor:
    company = _get_company(db, user)
    competitor = (
        db.query(Competitor)
        .filter(
            Competitor.id == competitor_id,
            Competitor.company_id == company.id,
            Competitor.is_active.is_(True),
        )
        .first()
    )
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competidor no encontrado")
    return competitor


def list_competitors(db: Session, user: User) -> list[Competitor]:
    company = _get_company(db, user)
    return (
        db.query(Competitor)
        .filter(
            Competitor.company_id == company.id,
            Competitor.is_active.is_(True),
        )
        .all()
    )


def create_competitor(db: Session, user: User, data: CompetitorCreate) -> Competitor:
    company = _get_company(db, user)
    active_count = (
        db.query(Competitor)
        .filter(
            Competitor.company_id == company.id,
            Competitor.is_active.is_(True),
        )
        .count()
    )
    if not is_within_limit(user.plan, active_count):
        from app.core.plans import competitor_limit  # noqa: PLC0415

        raise PlanLimitReached(plan=user.plan, limit=competitor_limit(user.plan) or 0)

    competitor = Competitor(
        company_id=company.id,
        name=data.name,
        website_url=data.website_url,
    )
    db.add(competitor)
    db.flush()

    for src in data.sources:
        db.add(
            CompetitorSource(
                competitor_id=competitor.id,
                source_type=src.source_type,
                source_url=src.source_url,
                config=src.config,
            )
        )

    db.commit()
    db.refresh(competitor)
    logger.info("competitors: creado id=%s company=%s", competitor.id, company.id)
    return competitor


def get_competitor(db: Session, competitor_id: uuid.UUID, user: User) -> Competitor:
    return _get_competitor_for_user(db, competitor_id, user)


def update_competitor(
    db: Session, competitor_id: uuid.UUID, user: User, data: CompetitorUpdate
) -> Competitor:
    competitor = _get_competitor_for_user(db, competitor_id, user)
    if data.name is not None:
        competitor.name = data.name
    if data.website_url is not None:
        competitor.website_url = data.website_url
    db.commit()
    db.refresh(competitor)
    return competitor


def delete_competitor(db: Session, competitor_id: uuid.UUID, user: User) -> None:
    competitor = _get_competitor_for_user(db, competitor_id, user)
    competitor.is_active = False
    db.commit()


# ─── Sources ─────────────────────────────────────────────────────────────────


def list_sources(db: Session, competitor_id: uuid.UUID, user: User) -> list[CompetitorSource]:
    competitor = _get_competitor_for_user(db, competitor_id, user)
    return (
        db.query(CompetitorSource)
        .filter(
            CompetitorSource.competitor_id == competitor.id,
            CompetitorSource.is_active.is_(True),
        )
        .all()
    )


def add_source(
    db: Session, competitor_id: uuid.UUID, user: User, data: SourceIn
) -> CompetitorSource:
    competitor = _get_competitor_for_user(db, competitor_id, user)
    source = CompetitorSource(
        competitor_id=competitor.id,
        source_type=data.source_type,
        source_url=data.source_url,
        config=data.config,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, competitor_id: uuid.UUID, source_id: uuid.UUID, user: User) -> None:
    _get_competitor_for_user(db, competitor_id, user)
    source = (
        db.query(CompetitorSource)
        .filter(
            CompetitorSource.id == source_id,
            CompetitorSource.competitor_id == competitor_id,
            CompetitorSource.is_active.is_(True),
        )
        .first()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    source.is_active = False
    db.commit()
