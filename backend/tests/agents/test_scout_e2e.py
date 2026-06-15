"""
Test de integración end-to-end del Scout Agent (DIX-35).

Verifica el flujo completo desde `run_daily_monitoring` hasta la creación de
`Snapshot` y `Change` en DB usando integraciones reales cuando es posible:

- Website: Playwright real sobre un servidor HTTP local con HTML controlado.
- MercadoLibre: modo real si hay credenciales, de lo contrario se salta.
- Apify: modo real si hay token, de lo contrario se salta.

Marcar con `@pytest.mark.integration` para correrlo explícitamente:
    cd backend && pytest tests/agents/test_scout_e2e.py -m integration -q

En CI hermético (sin credenciales ni browser) el test se auto-skipea.
"""

from __future__ import annotations

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  # registra todos los modelos en Base.metadata
from app.core.base import Base
from app.domains.auth.models import Company, User  # noqa: F401
from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.sources.models import CompetitorSource

pytestmark = pytest.mark.integration

_E2E_DB_PATH = Path(__file__).parent / ".." / "test_e2e.db"
_E2E_DATABASE_URL = f"sqlite:///{_E2E_DB_PATH}"


# ─── Playwright availability ──────────────────────────────────────────────────


def _chromium_available() -> bool:
    """True si Chromium de Playwright está instalado y arranca."""
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:  # noqa: BLE001
        return False


_CHROMIUM_AVAILABLE = _chromium_available()


# ─── DB fixtures (SQLite file para compartir entre sesiones del worker) ───────


@pytest.fixture(scope="module")
def e2e_engine():
    """Engine de SQLite en archivo para tests E2E."""
    os.environ["DATABASE_URL"] = _E2E_DATABASE_URL
    engine = create_engine(_E2E_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    _close_scout_sessions()
    engine.dispose()
    try:
        _E2E_DB_PATH.unlink(missing_ok=True)
    except PermissionError:
        # En Windows el archivo puede quedar bloqueado por conexiones internas
        # del worker; no es crítico para el test.
        pass


@pytest.fixture()
def e2e_db(e2e_engine):
    """Sesión de prueba sobre el engine E2E. Limpia las tablas en cada test."""
    Base.metadata.drop_all(e2e_engine)
    Base.metadata.create_all(e2e_engine)
    SessionLocal = sessionmaker(bind=e2e_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def e2e_user(e2e_db: Session) -> User:
    from app.domains.auth.service import upsert_user_from_clerk

    return upsert_user_from_clerk(e2e_db, clerk_id="e2e_user", email="e2e@vigi.ai", name="E2E")


class _MutableHandler(BaseHTTPRequestHandler):
    """Handler que devuelve el HTML almacenado en la clase."""

    html: str = "<html><body>Initial</body></html>"

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(self.html.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        pass


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def local_website_server():
    """Levanta un servidor HTTP local para tests de integración del scraper."""
    port = _find_free_port()
    server = HTTPServer(("127.0.0.1", port), _MutableHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    for _ in range(50):
        try:
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.1):
                break
        except Exception:  # noqa: BLE001
            time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    thread.join(timeout=2)


# ─── Helpers ──────────────────────────────────────────────────────────────────

_OPEN_SCOUT_SESSIONS: list[Session] = []


def _scout_session(e2e_engine) -> Session:
    """Devuelve una sesión fresca sobre el engine E2E (simulate SessionLocal)."""
    SessionLocal = sessionmaker(bind=e2e_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    _OPEN_SCOUT_SESSIONS.append(session)
    return session


def _close_scout_sessions() -> None:
    for session in _OPEN_SCOUT_SESSIONS:
        session.close()
    _OPEN_SCOUT_SESSIONS.clear()


def _count_snapshots(db: Session, source_id) -> int:
    return db.query(Snapshot).filter(Snapshot.source_id == source_id).count()


def _count_changes(db: Session, source_id) -> int:
    return db.query(Change).filter(Change.source_id == source_id).count()


# ─── Tests E2E semi-real ──────────────────────────────────────────────────────


@pytest.mark.skipif(
    not _CHROMIUM_AVAILABLE,
    reason="Chromium de Playwright no instalado: correr `playwright install chromium`",
)
class TestScoutEndToEndSemiReal:
    def test_website_source_creates_snapshot_and_change(
        self, e2e_engine, e2e_db, e2e_user, local_website_server
    ):
        """Flujo E2E semi-real: website con Playwright sobre servidor local."""
        company = e2e_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E Semi Real",
            website_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(competitor)
        e2e_db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(source)
        e2e_db.flush()
        source_id = source.id
        competitor_id = competitor.id
        e2e_db.commit()

        _MutableHandler.html = "<html><body><h1>Precio: $100</h1></body></html>"

        from app.workers.tasks import scout_competitor as scout_competitor_task

        with (
            patch("app.workers.tasks.SessionLocal", lambda: _scout_session(e2e_engine)),
            patch("app.core.config.settings.use_mocks", False),
            patch("app.workers.tasks.analyze_change") as mock_analyze,
            patch.object(scout_competitor_task, "delay") as mock_scout_delay,
        ):
            from app.workers.tasks import scout_competitor

            mock_analyze.delay = lambda x: None
            mock_scout_delay.side_effect = lambda cid: scout_competitor(cid)

            from app.workers.tasks import run_daily_monitoring

            run_daily_monitoring()

        db = _scout_session(e2e_engine)
        assert _count_snapshots(db, source_id) == 1
        assert _count_changes(db, source_id) == 0

        snapshot = db.query(Snapshot).filter(Snapshot.source_id == source_id).first()
        assert snapshot is not None
        assert "Precio: $100" in snapshot.content
        assert len(snapshot.content_hash) == 64
        db.close()

        _MutableHandler.html = "<html><body><h1>Precio: $150</h1></body></html>"

        with (
            patch("app.workers.tasks.SessionLocal", lambda: _scout_session(e2e_engine)),
            patch("app.core.config.settings.use_mocks", False),
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            from app.workers.tasks import scout_competitor

            mock_analyze.delay = lambda x: None
            scout_competitor(str(competitor_id))

        db = _scout_session(e2e_engine)
        assert _count_snapshots(db, source_id) == 2
        assert _count_changes(db, source_id) == 1

        change = db.query(Change).filter(Change.source_id == source_id).first()
        assert change is not None
        assert change.status == "pending"
        assert change.section == "pricing"
        assert "Precio: $150" in change.diff_text
        assert "Precio: $100" in change.diff_text
        db.close()

    def test_website_source_is_idempotent_on_third_run(
        self, e2e_engine, e2e_db, e2e_user, local_website_server
    ):
        """Tercera ejecución con el mismo contenido no genera Change duplicado."""
        company = e2e_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E Idempotent",
            website_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(competitor)
        e2e_db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(source)
        e2e_db.flush()
        source_id = source.id
        competitor_id = competitor.id
        e2e_db.commit()

        _MutableHandler.html = "<html><body><h1>Producto A</h1></body></html>"

        with (
            patch("app.workers.tasks.SessionLocal", lambda: _scout_session(e2e_engine)),
            patch("app.core.config.settings.use_mocks", False),
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            from app.workers.tasks import scout_competitor

            mock_analyze.delay = lambda x: None
            scout_competitor(str(competitor_id))
            scout_competitor(str(competitor_id))
            scout_competitor(str(competitor_id))

        db = _scout_session(e2e_engine)
        assert _count_snapshots(db, source_id) == 1
        assert _count_changes(db, source_id) == 0

        updated_source = db.query(CompetitorSource).filter(CompetitorSource.id == source_id).first()
        assert updated_source.last_checked_at is not None
        db.close()

    def test_multiple_sources_with_one_website_real(
        self, e2e_engine, e2e_db, e2e_user, local_website_server
    ):
        """Competidor con website real + ML/Apify mock: todas se procesan."""
        company = e2e_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E Multi Source",
            website_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(competitor)
        e2e_db.flush()

        website = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url=local_website_server,
            is_active=True,
        )
        ml = CompetitorSource(
            competitor_id=competitor.id,
            source_type="mercadolibre",
            config={"seller_id": "123"},
            is_active=True,
        )
        jobs = CompetitorSource(
            competitor_id=competitor.id,
            source_type="jobs",
            is_active=True,
        )
        e2e_db.add_all([website, ml, jobs])
        e2e_db.flush()
        website_id = website.id
        ml_id = ml.id
        jobs_id = jobs.id
        competitor_id = competitor.id
        e2e_db.commit()

        _MutableHandler.html = "<html><body><h1>Catálogo</h1></body></html>"

        with (
            patch("app.workers.tasks.SessionLocal", lambda: _scout_session(e2e_engine)),
            patch("app.core.config.settings.use_mocks", False),
            patch("app.workers.tasks.analyze_change") as mock_analyze,
            patch("app.agents.scout.strategies.get_seller_state") as mock_ml,
            patch("app.agents.scout.strategies.get_job_postings") as mock_jobs,
        ):
            from app.workers.tasks import scout_competitor

            mock_analyze.delay = lambda x: None
            mock_ml.return_value = {"seller_id": "123", "active_listings": 10}
            mock_jobs.return_value = [{"title": "Dev", "company": "E2E"}]
            scout_competitor(str(competitor_id))

        db = _scout_session(e2e_engine)
        assert _count_snapshots(db, website_id) == 1
        assert _count_snapshots(db, ml_id) == 1
        assert _count_snapshots(db, jobs_id) == 1

        mock_ml.assert_called_once_with("123")
        mock_jobs.assert_called_once_with("E2E Multi Source", since_days=30)
        db.close()


# ─── Tests E2E con integraciones reales (requieren credenciales) ──────────────


class TestScoutEndToEndRealIntegrations:
    @pytest.mark.skipif(
        not bool(os.environ.get("ML_CLIENT_ID") and os.environ.get("ML_CLIENT_SECRET")),
        reason="Requiere ML_CLIENT_ID y ML_CLIENT_SECRET",
    )
    def test_mercadolibre_real_seller_state(
        self, e2e_engine, e2e_db, e2e_user, local_website_server
    ):
        """E2E real con MercadoLibre (solo si hay credenciales)."""
        company = e2e_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E ML Real",
            website_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(competitor)
        e2e_db.flush()

        seller_id = os.environ.get("ML_TEST_SELLER_ID", "123")
        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="mercadolibre",
            config={"seller_id": seller_id},
            is_active=True,
        )
        e2e_db.add(source)
        e2e_db.flush()
        source_id = source.id
        competitor_id = competitor.id
        e2e_db.commit()

        with (
            patch("app.workers.tasks.SessionLocal", lambda: _scout_session(e2e_engine)),
            patch("app.core.config.settings.use_mocks", False),
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            from app.workers.tasks import scout_competitor

            mock_analyze.delay = MagicMock()
            scout_competitor(str(competitor_id))

        db = _scout_session(e2e_engine)
        assert db.query(Snapshot).filter(Snapshot.source_id == source_id).count() >= 1
        db.close()

    @pytest.mark.skipif(
        not bool(os.environ.get("APIFY_TOKEN")),
        reason="Requiere APIFY_TOKEN",
    )
    def test_apify_real_job_postings(self, e2e_engine, e2e_db, e2e_user, local_website_server):
        """E2E real con Apify (solo si hay token)."""
        company = e2e_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E Apify Real",
            website_url=local_website_server,
            is_active=True,
        )
        e2e_db.add(competitor)
        e2e_db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="jobs",
            is_active=True,
        )
        e2e_db.add(source)
        e2e_db.flush()
        source_id = source.id
        competitor_id = competitor.id
        e2e_db.commit()

        with (
            patch("app.workers.tasks.SessionLocal", lambda: _scout_session(e2e_engine)),
            patch("app.core.config.settings.use_mocks", False),
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            from app.workers.tasks import scout_competitor

            mock_analyze.delay = MagicMock()
            scout_competitor(str(competitor_id))

        db = _scout_session(e2e_engine)
        assert db.query(Snapshot).filter(Snapshot.source_id == source_id).count() >= 1
        db.close()
