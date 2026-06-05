"""
Seed de datos mockeados para la BD de staging.

Crea usuarios, empresas, competidores, fuentes, cambios e insights realistas
para que el entorno de staging/dev tenga datos con los que trabajar.

Idempotente: si los datos ya existen (detectado por clerk_id), no los duplica.

Uso:
    cd backend
    DATABASE_URL=postgresql+psycopg://... python scripts/seed_staging.py
"""

import os
import sys
from datetime import UTC, datetime, timedelta

# Asegurar que el path incluya el backend para importar app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("USE_MOCKS", "true")
os.environ.setdefault("SECRET_KEY", "seed-script-not-real")
os.environ.setdefault("CLERK_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("CLERK_JWKS_URL", "https://fake.clerk.dev/.well-known/jwks.json")
os.environ.setdefault("CLERK_WEBHOOK_SECRET", "whsec_fake")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.domains.auth.models import Company, User
from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.insights.models import Insight
from app.domains.sources.models import CompetitorSource

DATABASE_URL = os.environ["DATABASE_URL"]

NOW = datetime.now(UTC)


def seed(db) -> None:  # type: ignore[no-untyped-def]
    # ─── Usuarios ────────────────────────────────────────────────────────────

    user_free = _upsert_user(
        db,
        clerk_id="seed_user_free",
        email="demo@norte-dist.com.ar",
        name="Marcos Pérez",
        plan="free",
        company_name="Distribuidora Norte SA",
        industry="food",
    )

    user_growth = _upsert_user(
        db,
        clerk_id="seed_user_growth",
        email="demo@techdist.com.ar",
        name="Laura Gómez",
        plan="growth",
        company_name="Tech Distribuciones SRL",
        industry="tech",
    )

    user_starter = _upsert_user(
        db,
        clerk_id="seed_user_starter",
        email="demo@construmat.com.ar",
        name="Roberto Silva",
        plan="starter",
        company_name="ConstruMat Distribuciones",
        industry="construction",
    )

    db.commit()
    print("✓ Usuarios y empresas")

    # ─── Competidores ─────────────────────────────────────────────────────────

    # free: max 2
    comp_norte_1 = _upsert_competitor(
        db, user_free.company, "Alimentos del Sur", "https://alimentosdelsur.com.ar"
    )
    comp_norte_2 = _upsert_competitor(
        db, user_free.company, "Distribuidora Pampa", "https://distpampa.com.ar"
    )

    # growth: max 10, ponemos 4
    comp_tech_1 = _upsert_competitor(
        db, user_growth.company, "TechSupply AR", "https://techsupply.com.ar"
    )
    comp_tech_2 = _upsert_competitor(
        db, user_growth.company, "Compuparts SRL", "https://compuparts.com.ar"
    )
    comp_tech_3 = _upsert_competitor(
        db, user_growth.company, "DigitalDist", "https://digitaldist.com.ar"
    )
    comp_tech_4 = _upsert_competitor(
        db, user_growth.company, "MercaTech", "https://mercatech.com.ar"
    )

    # starter: max 5, ponemos 3
    comp_const_1 = _upsert_competitor(
        db, user_starter.company, "CementoPlus", "https://cementoplus.com.ar"
    )
    comp_const_2 = _upsert_competitor(
        db, user_starter.company, "Ferretería Central", "https://ferreteriacentral.com.ar"
    )
    comp_const_3 = _upsert_competitor(
        db, user_starter.company, "MateriaBuild", "https://materiabuild.com.ar"
    )

    db.commit()
    print("✓ Competidores")

    # ─── Fuentes ─────────────────────────────────────────────────────────────

    src_norte_1_web = _upsert_source(
        db, comp_norte_1, "website", "https://alimentosdelsur.com.ar/precios"
    )
    src_norte_2_web = _upsert_source(db, comp_norte_2, "website", "https://distpampa.com.ar")
    _upsert_source(db, comp_norte_2, "mercadolibre", None, config={"seller_id": "12345678"})

    _upsert_source(db, comp_tech_1, "website", "https://techsupply.com.ar/catalogo")
    src_tech_1_jobs = _upsert_source(db, comp_tech_1, "jobs", "https://techsupply.com.ar/empleos")
    src_tech_2_web = _upsert_source(db, comp_tech_2, "website", "https://compuparts.com.ar")
    _upsert_source(db, comp_tech_2, "mercadolibre", None, config={"seller_id": "87654321"})
    src_tech_3_web = _upsert_source(
        db, comp_tech_3, "website", "https://digitaldist.com.ar/precios"
    )
    _upsert_source(db, comp_tech_4, "website", "https://mercatech.com.ar")

    src_const_1_web = _upsert_source(
        db, comp_const_1, "website", "https://cementoplus.com.ar/lista-precios"
    )
    _upsert_source(db, comp_const_2, "website", "https://ferreteriacentral.com.ar")
    _upsert_source(db, comp_const_3, "website", "https://materiabuild.com.ar")

    db.commit()
    print("✓ Fuentes")

    # ─── Cambios e insights ───────────────────────────────────────────────────

    # Cambio done con insight — precio de competidor bajó
    _upsert_change_with_insight(
        db,
        competitor=comp_norte_1,
        source=src_norte_1_web,
        section="pricing",
        diff_text=(
            "- Aceite girasol 5L: $4.200\n+ Aceite girasol 5L: $3.850\n"
            "- Harina 25kg: $8.900\n+ Harina 25kg: $8.400"
        ),
        status="done",
        detected_at=NOW - timedelta(hours=3),
        what_changed="Alimentos del Sur bajó precios en aceite (-8%) y harina (-6%).",
        why_it_matters="Si no ajustás tus precios, perdés clientes en esos productos.",
        what_to_do="Revisá tu margen en aceite y harina. Considerá bajar entre un 5-7% para no perder competitividad.",
        urgency="alta",
    )

    # Cambio done con insight — nuevo puesto de trabajo (señal de expansión)
    _upsert_change_with_insight(
        db,
        competitor=comp_tech_1,
        source=src_tech_1_jobs,
        section="jobs",
        diff_text="+ Vendedor mayorista zona norte (publicado hace 2 días)\n+ Coordinador de depósito (publicado hace 1 día)",
        status="done",
        detected_at=NOW - timedelta(hours=8),
        what_changed="TechSupply AR publicó 2 nuevos puestos: vendedor mayorista y coordinador de depósito.",
        why_it_matters="Están expandiendo su fuerza de ventas en tu zona. Probablemente preparan un push comercial.",
        what_to_do="Reforzá la relación con tus clientes actuales antes de que lleguen. Ofrecé condiciones especiales de fidelización.",
        urgency="media",
    )

    # Cambio done con insight — cambio de catálogo
    _upsert_change_with_insight(
        db,
        competitor=comp_tech_2,
        source=src_tech_2_web,
        section="features",
        diff_text=(
            "+ Sección nueva: 'Accesorios Gaming'\n"
            "+ 47 productos nuevos en periféricos\n"
            "- Sección eliminada: 'Impresoras Laser'"
        ),
        status="done",
        detected_at=NOW - timedelta(days=1),
        what_changed="Compuparts SRL agregó 47 productos de gaming y eliminó la sección de impresoras laser.",
        why_it_matters="Se están reposicionando hacia gaming. Si vos también vendés esa categoría, hay competencia directa nueva.",
        what_to_do="Evaluá tu oferta de gaming. Si no tenés esa categoría, es una oportunidad para diferenciarte con servicio técnico.",
        urgency="media",
    )

    # Cambio pending — todavía no analizado
    _upsert_change_only(
        db,
        competitor=comp_const_1,
        source=src_const_1_web,
        section="pricing",
        diff_text="- Cemento Portland 50kg: $3.100\n+ Cemento Portland 50kg: $3.450",
        status="pending",
        detected_at=NOW - timedelta(minutes=30),
    )

    # Cambio analyzing
    _upsert_change_only(
        db,
        competitor=comp_norte_2,
        source=src_norte_2_web,
        section="home",
        diff_text='- "Envíos en 24hs"\n+ "Envíos en 48hs — temporada alta"',
        status="analyzing",
        detected_at=NOW - timedelta(minutes=15),
    )

    # Cambio failed
    _upsert_change_only(
        db,
        competitor=comp_tech_3,
        source=src_tech_3_web,
        section="pricing",
        diff_text="[contenido demasiado grande para analizar — 48kb de diff]",
        status="failed",
        detected_at=NOW - timedelta(hours=5),
    )

    db.commit()
    print("✓ Cambios e insights")
    print("\nSeed completado.")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _upsert_user(db, clerk_id, email, name, plan, company_name, industry):  # type: ignore[no-untyped-def]
    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if user is None:
        user = User(clerk_id=clerk_id, email=email, name=name, plan=plan)
        db.add(user)
        db.flush()
        company = Company(user_id=user.id, name=company_name, industry=industry)
        db.add(company)
        db.flush()
        db.refresh(user)
    return user


def _upsert_competitor(db, company, name, website_url):  # type: ignore[no-untyped-def]
    comp = (
        db.query(Competitor)
        .filter(
            Competitor.company_id == company.id,
            Competitor.name == name,
        )
        .first()
    )
    if comp is None:
        comp = Competitor(company_id=company.id, name=name, website_url=website_url)
        db.add(comp)
        db.flush()
    return comp


def _upsert_source(db, competitor, source_type, source_url, config=None):  # type: ignore[no-untyped-def]
    src = (
        db.query(CompetitorSource)
        .filter(
            CompetitorSource.competitor_id == competitor.id,
            CompetitorSource.source_type == source_type,
        )
        .first()
    )
    if src is None:
        src = CompetitorSource(
            competitor_id=competitor.id,
            source_type=source_type,
            source_url=source_url,
            config=config,
        )
        db.add(src)
        db.flush()
    return src


def _upsert_change_only(db, competitor, source, section, diff_text, status, detected_at):  # type: ignore[no-untyped-def]
    existing = (
        db.query(Change)
        .filter(
            Change.competitor_id == competitor.id,
            Change.source_id == source.id,
            Change.section == section,
            Change.status == status,
        )
        .first()
    )
    if existing:
        return existing

    snap_after = Snapshot(
        competitor_id=competitor.id,
        source_id=source.id,
        source_type=source.source_type,
        content_hash="seed_" + section + "_" + status,
        content="[contenido del snapshot - seed]",
        captured_at=detected_at,
    )
    db.add(snap_after)
    db.flush()

    change = Change(
        competitor_id=competitor.id,
        source_id=source.id,
        source_type=source.source_type,
        section=section,
        diff_text=diff_text,
        snapshot_after_id=snap_after.id,
        detected_at=detected_at,
        status=status,
    )
    db.add(change)
    db.flush()
    return change


def _upsert_change_with_insight(  # type: ignore[no-untyped-def]
    db,
    competitor,
    source,
    section,
    diff_text,
    status,
    detected_at,
    what_changed,
    why_it_matters,
    what_to_do,
    urgency,
):
    change = _upsert_change_only(db, competitor, source, section, diff_text, status, detected_at)

    if db.query(Insight).filter(Insight.change_id == change.id).first():
        return

    insight = Insight(
        change_id=change.id,
        what_changed=what_changed,
        why_it_matters=why_it_matters,
        what_to_do=what_to_do,
        urgency=urgency,
        llm_model="gemini/gemini-2.0-flash",
        prompt_tokens=420,
        completion_tokens=180,
        generated_at=detected_at + timedelta(seconds=12),
    )
    db.add(insight)
    db.flush()


if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Session = sessionmaker(bind=engine)
    with Session() as db:
        seed(db)
