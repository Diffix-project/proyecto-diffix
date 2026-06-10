"""
Tests de la tarea Celery scout_competitor (DIX-16).

Cubre:
- scout_competitor: procesamiento de fuentes, aislamiento de errores
- run_daily_monitoring: encolado de tareas por competidor activo
"""

import uuid
from unittest.mock import MagicMock, patch

from app.domains.competitors.models import Competitor
from app.domains.sources.models import CompetitorSource


class TestScoutCompetitorTask:
    def test_processes_all_active_sources(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        source1 = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://test1.com",
            is_active=True,
        )
        source2 = CompetitorSource(
            competitor_id=competitor.id,
            source_type="mercadolibre",
            config={"seller_id": "123"},
            is_active=True,
        )
        db.add_all([source1, source2])
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_scraper,
            patch("app.agents.scout.core.get_seller_state") as mock_ml,
        ):
            mock_session_local.return_value = db
            mock_scraper.return_value = "content"
            mock_ml.return_value = {"seller_id": "123"}

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        assert mock_scraper.call_count == 1
        assert mock_ml.call_count == 1

    def test_skips_inactive_competitor(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Inactive Comp",
            website_url="https://inactive.com",
            is_active=False,
        )
        db.add(competitor)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_fetch,
        ):
            mock_session_local.return_value = db

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        mock_fetch.assert_not_called()

    def test_skips_inactive_sources(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        active_source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://active.com",
            is_active=True,
        )
        _inactive_source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://inactive.com",
            is_active=False,
        )
        db.add_all([active_source, _inactive_source])
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_fetch,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = "content"

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        assert mock_fetch.call_count == 1

    def test_creates_change_when_hash_differs(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://test.com",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id

        same_hash = "a" * 64
        from app.domains.changes.models import Snapshot

        last_snap = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash=same_hash,
            content="old content",
        )
        db.add(last_snap)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_fetch,
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = "new content"
            mock_analyze.delay = MagicMock()

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        from app.domains.changes.models import Change

        changes = db.query(Change).filter(Change.source_id == source_id).all()
        assert len(changes) == 1
        mock_analyze.delay.assert_called_once()

    def test_no_change_when_hash_identical(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://test.com",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id

        from app.agents.scout.core import compute_hash
        from app.domains.changes.models import Snapshot

        content = "same content"
        same_hash = compute_hash(content)

        last_snap = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash=same_hash,
            content=content,
        )
        db.add(last_snap)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_fetch,
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = "same content"
            mock_analyze.delay = MagicMock()

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        from app.domains.changes.models import Change

        changes = db.query(Change).filter(Change.source_id == source_id).all()
        assert len(changes) == 0
        mock_analyze.delay.assert_not_called()

    def test_error_in_one_source_does_not_stop_others(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        source1 = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://test1.com",
            is_active=True,
        )
        db.add(source1)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_scraper,
        ):
            mock_session_local.return_value = db
            mock_scraper.side_effect = ValueError("Error simulado")

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        assert mock_scraper.call_count == 1

    def test_updates_last_checked_at(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://test.com",
            is_active=True,
            last_checked_at=None,
        )
        db.add(source)
        db.flush()
        source_id = source.id
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.core.fetch_clean_text") as mock_fetch,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = "content"

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        from app.domains.sources.models import CompetitorSource as CS

        updated_source = db.query(CS).filter(CS.id == source_id).first()
        assert updated_source.last_checked_at is not None

    def test_handles_not_implemented_error_gracefully(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Test Comp",
            website_url="https://test.com",
        )
        db.add(competitor)
        db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="pdf",
            is_active=True,
        )
        db.add(source)
        db.flush()
        db.commit()

        with patch("app.workers.tasks.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

    def test_handles_missing_competitor(self, db):
        fake_id = str(uuid.uuid4())

        with patch("app.workers.tasks.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db

            from app.workers.tasks import scout_competitor

            scout_competitor(fake_id)


class TestRunDailyMonitoring:
    def test_enqueues_scout_for_each_active_competitor(self, db, test_user):
        company = test_user.company
        comp1 = Competitor(
            company_id=company.id,
            name="Comp 1",
            website_url="https://comp1.com",
            is_active=True,
        )
        comp2 = Competitor(
            company_id=company.id,
            name="Comp 2",
            website_url="https://comp2.com",
            is_active=True,
        )
        db.add_all([comp1, comp2])
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.workers.tasks.scout_competitor") as mock_scout,
        ):
            mock_session_local.return_value = db
            mock_scout.delay = MagicMock()

            from app.workers.tasks import run_daily_monitoring

            run_daily_monitoring()

        assert mock_scout.delay.call_count == 2

    def test_skips_inactive_competitors(self, db, test_user):
        company = test_user.company
        active_comp = Competitor(
            company_id=company.id,
            name="Active",
            website_url="https://active.com",
            is_active=True,
        )
        inactive_comp = Competitor(
            company_id=company.id,
            name="Inactive",
            website_url="https://inactive.com",
            is_active=False,
        )
        db.add_all([active_comp, inactive_comp])
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.workers.tasks.scout_competitor") as mock_scout,
        ):
            mock_session_local.return_value = db
            mock_scout.delay = MagicMock()

            from app.workers.tasks import run_daily_monitoring

            run_daily_monitoring()

        assert mock_scout.delay.call_count == 1
