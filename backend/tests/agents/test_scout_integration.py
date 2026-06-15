"""
Test de integración end-to-end del Scout Agent (DIX-17).

Verifica el flujo completo desde run_daily_monitoring hasta la creación de Changes.
"""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.sources.models import CompetitorSource

# ─── Helpers de conteo para assertions de idempotencia ────────────────────────


def count_snapshots(db: Session, source_id) -> int:
    """Cuenta snapshots de una fuente."""
    return db.query(Snapshot).filter(Snapshot.source_id == source_id).count()


def count_changes(db: Session, source_id) -> int:
    """Cuenta changes de una fuente."""
    return db.query(Change).filter(Change.source_id == source_id).count()


class TestScoutEndToEnd:
    def test_complete_flow_from_monitoring_to_changes(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E Test Comp",
            website_url="https://e2e.com",
            is_active=True,
        )
        db.add(competitor)
        db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://e2e.com/products",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id
        db.commit()

        from app.workers.tasks import scout_competitor

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.strategies.fetch_clean_text") as mock_fetch,
            patch("app.workers.tasks.analyze_change") as mock_analyze,
            patch("app.workers.tasks.scout_competitor") as mock_scout,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = "Producto A: $100\nProducto B: $200"
            mock_analyze.delay = lambda x: None
            mock_scout.delay = lambda cid: scout_competitor(cid)

            from app.workers.tasks import run_daily_monitoring

            run_daily_monitoring()

        db.expire_all()

        snapshots = db.query(Snapshot).filter(Snapshot.source_id == source_id).all()
        assert len(snapshots) == 1
        assert snapshots[0].content == "Producto A: $100\nProducto B: $200"
        assert len(snapshots[0].content_hash) == 64

        changes = db.query(Change).filter(Change.source_id == source_id).all()
        assert len(changes) == 0

        db.expire_all()
        updated_source = db.query(CompetitorSource).filter(CompetitorSource.id == source_id).first()
        assert updated_source.last_checked_at is not None

    def test_second_run_with_changes(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="E2E Test Comp 2",
            website_url="https://e2e2.com",
            is_active=True,
        )
        db.add(competitor)
        db.flush()

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://e2e2.com/products",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id

        from app.agents.scout.core import compute_hash

        first_content = "Producto A: $100"
        first_hash = compute_hash(first_content)

        first_snapshot = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash=first_hash,
            content=first_content,
        )
        db.add(first_snapshot)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.strategies.fetch_clean_text") as mock_fetch,
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = "Producto A: $150\nProducto B: $200"
            mock_analyze.delay = lambda x: None

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor.id))

        db.expire_all()

        snapshots = db.query(Snapshot).filter(Snapshot.source_id == source_id).all()
        assert len(snapshots) == 2

        changes = db.query(Change).filter(Change.source_id == source_id).all()
        assert len(changes) == 1
        change = changes[0]
        assert change.status == "pending"
        assert change.section == "pricing"
        assert "+Producto A: $150" in change.diff_text
        assert "+Producto B: $200" in change.diff_text
        assert "-Producto A: $100" in change.diff_text
        assert change.diff_raw is not None
        assert "added" in change.diff_raw
        assert "removed" in change.diff_raw

    def test_idempotency_no_duplicate_changes(self, db, test_user):
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="Idempotency Test",
            website_url="https://idem.com",
            is_active=True,
        )
        db.add(competitor)
        db.flush()
        competitor_id = competitor.id

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://idem.com",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id

        from app.agents.scout.core import compute_hash

        content = "Contenido estable"
        content_hash = compute_hash(content)

        snapshot = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash=content_hash,
            content=content,
        )
        db.add(snapshot)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.strategies.fetch_clean_text") as mock_fetch,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = content

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor_id))
            scout_competitor(str(competitor_id))
            scout_competitor(str(competitor_id))

        db.expire_all()

        assert count_snapshots(db, source_id) == 1
        assert count_changes(db, source_id) == 0

    def test_idempotency_a_to_b_to_a_generates_two_changes(self, db, test_user):
        """
        Transiciones A -> B -> A deben generar exactamente 2 Changes:
        uno por el cambio a B y otro por el regreso a A.
        """
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="A-B-A Test",
            website_url="https://aba.com",
            is_active=True,
        )
        db.add(competitor)
        db.flush()
        competitor_id = competitor.id

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://aba.com",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id

        from app.agents.scout.core import compute_hash

        content_a = "Precio A: $100"
        content_b = "Precio A: $150"

        first_snapshot = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash=compute_hash(content_a),
            content=content_a,
        )
        db.add(first_snapshot)
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.strategies.fetch_clean_text") as mock_fetch,
            patch("app.workers.tasks.analyze_change") as mock_analyze,
        ):
            mock_session_local.return_value = db
            mock_analyze.delay = lambda x: None

            from app.workers.tasks import scout_competitor

            # A -> B: debe crear Change
            mock_fetch.return_value = content_b
            scout_competitor(str(competitor_id))

            # B -> A: debe crear otro Change
            mock_fetch.return_value = content_a
            scout_competitor(str(competitor_id))

        db.expire_all()

        assert count_snapshots(db, source_id) == 3  # inicial + B + A
        assert count_changes(db, source_id) == 2

        changes = (
            db.query(Change)
            .filter(Change.source_id == source_id)
            .order_by(Change.detected_at)
            .all()
        )
        assert changes[0].snapshot_before.content == content_a
        assert changes[0].snapshot_after.content == content_b
        assert changes[1].snapshot_before.content == content_b
        assert changes[1].snapshot_after.content == content_a

    def test_hash_consistency_same_content_same_hash(self, db, test_user):
        """El hash SHA256 debe ser determinista para el mismo contenido."""
        from app.agents.scout.core import compute_hash

        content = "Contenido determinista del Scout"
        assert compute_hash(content) == compute_hash(content)
        assert len(compute_hash(content)) == 64

    def test_no_duplicate_snapshots_for_same_hash(self, db, test_user):
        """Scout no debe crear un snapshot nuevo si el hash no cambió."""
        company = test_user.company
        competitor = Competitor(
            company_id=company.id,
            name="No Duplicate Snapshot",
            website_url="https://nodup.com",
            is_active=True,
        )
        db.add(competitor)
        db.flush()
        competitor_id = competitor.id

        source = CompetitorSource(
            competitor_id=competitor.id,
            source_type="website",
            source_url="https://nodup.com",
            is_active=True,
        )
        db.add(source)
        db.flush()
        source_id = source.id

        from app.agents.scout.core import compute_hash

        content = "Contenido sin cambios"
        content_hash = compute_hash(content)

        db.add(
            Snapshot(
                competitor_id=competitor.id,
                source_id=source.id,
                source_type="website",
                content_hash=content_hash,
                content=content,
            )
        )
        db.commit()

        with (
            patch("app.workers.tasks.SessionLocal") as mock_session_local,
            patch("app.agents.scout.strategies.fetch_clean_text") as mock_fetch,
        ):
            mock_session_local.return_value = db
            mock_fetch.return_value = content

            from app.workers.tasks import scout_competitor

            scout_competitor(str(competitor_id))

        db.expire_all()

        assert count_snapshots(db, source_id) == 1
        assert count_changes(db, source_id) == 0
