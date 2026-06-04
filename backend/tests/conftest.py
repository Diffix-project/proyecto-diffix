import os

os.environ.setdefault("USE_MOCKS", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.base import Base
from app.domains.auth.models import Company, User  # noqa: F401
from app.domains.changes.models import Change, Snapshot  # noqa: F401
from app.domains.competitors.models import Competitor  # noqa: F401
from app.domains.digests.models import Digest  # noqa: F401
from app.domains.insights.models import Insight  # noqa: F401
from app.domains.notifications.models import Notification  # noqa: F401
from app.domains.sources.models import CompetitorSource  # noqa: F401

DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():
    kwargs = {}
    if DATABASE_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    eng = create_engine(DATABASE_URL, **kwargs)

    if DATABASE_URL.startswith("postgresql"):
        with eng.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db: Session):
    from app.core.database import get_db
    from app.main import app

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ─── Helpers de datos de prueba ───────────────────────────────────────────────


@pytest.fixture()
def test_user(db: Session) -> User:
    from app.domains.auth.service import upsert_user_from_clerk

    return upsert_user_from_clerk(db, clerk_id="mock_clerk_user", email="dev@vigi.ai", name="Dev")


@pytest.fixture()
def test_user_growth(db: Session) -> User:
    from app.domains.auth.service import upsert_user_from_clerk

    user = upsert_user_from_clerk(
        db, clerk_id="mock_clerk_growth", email="growth@vigi.ai", name="Growth User"
    )
    user.plan = "growth"
    db.commit()
    db.refresh(user)
    return user


def make_competitor(db: Session, company: Company, name: str = "Acme") -> Competitor:
    competitor = Competitor(
        company_id=company.id,
        name=name,
        website_url=f"https://{name.lower()}.com",
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor
