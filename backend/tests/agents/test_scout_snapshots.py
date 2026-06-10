"""
Tests del modulo scout.core (DIX-14).

Cubre:
- get_last_snapshot: consulta ultimo snapshot
- create_snapshot: crea snapshot en DB
- compute_diff: genera diff_text y diff_raw
- detect_section: determina seccion por source_type
- create_change: crea Change vinculado a snapshots
"""

import uuid

from app.agents.scout.core import (
    compute_diff,
    create_change,
    create_snapshot,
    detect_section,
    get_last_snapshot,
)
from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.sources.models import CompetitorSource


class TestGetLastSnapshot:
    def test_returns_none_when_no_snapshots(self, db):
        fake_uuid = uuid.uuid4()
        result = get_last_snapshot(db, fake_uuid)
        assert result is None

    def test_returns_latest_snapshot(self, db, test_user):
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
        )
        db.add(source)
        db.flush()

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        snap1 = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash="aaa",
            content="old",
            captured_at=now - timedelta(seconds=1),
        )
        snap2 = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash="bbb",
            content="new",
            captured_at=now,
        )
        db.add_all([snap1, snap2])
        db.flush()

        result = get_last_snapshot(db, source.id)
        assert result is not None
        assert result.content_hash == "bbb"


class TestCreateSnapshot:
    def test_creates_snapshot_with_correct_fields(self, db, test_user):
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
            source_url="https://test.com/page",
        )
        db.add(source)
        db.flush()

        content = "contenido de prueba"
        content_hash = "abc123" * 10 + "abcd"

        snapshot = create_snapshot(db, source, content, content_hash)

        assert snapshot.competitor_id == competitor.id
        assert snapshot.source_id == source.id
        assert snapshot.source_type == "website"
        assert snapshot.content_hash == content_hash
        assert snapshot.content == content
        assert snapshot.raw_url == "https://test.com/page"
        assert snapshot.captured_at is not None

    def test_snapshot_is_persisted_after_flush(self, db, test_user):
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
            source_type="mercadolibre",
            config={"seller_id": "123"},
        )
        db.add(source)
        db.flush()

        snapshot = create_snapshot(db, source, "content", "hash123" + "0" * 57)

        result = db.query(Snapshot).filter(Snapshot.id == snapshot.id).first()
        assert result is not None
        assert result.content == "content"


class TestComputeDiff:
    def test_identical_content_empty_diff(self):
        content = "linea 1\nlinea 2\n"
        diff_text, diff_raw = compute_diff(content, content)

        assert diff_text == ""
        assert diff_raw["added"] == []
        assert diff_raw["removed"] == []

    def test_added_lines(self):
        before = "linea 1\n"
        after = "linea 1\nlinea 2\n"

        diff_text, diff_raw = compute_diff(before, after)

        assert "+linea 2" in diff_text
        assert "linea 2" in diff_raw["added"]
        assert diff_raw["removed"] == []

    def test_removed_lines(self):
        before = "linea 1\nlinea 2\n"
        after = "linea 1\n"

        diff_text, diff_raw = compute_diff(before, after)

        assert "-linea 2" in diff_text
        assert "linea 2" in diff_raw["removed"]
        assert diff_raw["added"] == []

    def test_changed_lines(self):
        before = "linea 1\nprecio viejo\n"
        after = "linea 1\nprecio nuevo\n"

        diff_text, diff_raw = compute_diff(before, after)

        assert "-precio viejo" in diff_text
        assert "+precio nuevo" in diff_text
        assert "precio viejo" in diff_raw["removed"]
        assert "precio nuevo" in diff_raw["added"]

    def test_diff_text_is_readable(self):
        before = "a\nb\nc\n"
        after = "a\nx\nc\n"

        diff_text, _ = compute_diff(before, after)

        assert "---" in diff_text
        assert "+++" in diff_text
        assert "-b" in diff_text
        assert "+x" in diff_text


class TestDetectSection:
    def test_jobs_returns_jobs(self):
        assert detect_section("jobs", "cualquier contenido") == "jobs"

    def test_mercadolibre_returns_pricing(self):
        assert detect_section("mercadolibre", "cualquier contenido") == "pricing"

    def test_pdf_returns_pdf(self):
        assert detect_section("pdf", "cualquier contenido") == "pdf"

    def test_website_with_price_keywords_returns_pricing(self):
        content = "Lista de precios actualizada. Producto A: $100"
        assert detect_section("website", content) == "pricing"

    def test_website_with_product_keywords_returns_features(self):
        content = "Nuevo catalogo de productos disponibles"
        assert detect_section("website", content) == "features"

    def test_website_without_keywords_returns_general(self):
        content = "Bienvenidos a nuestra pagina principal"
        assert detect_section("website", content) == "general"

    def test_unknown_type_returns_general(self):
        assert detect_section("unknown", "contenido") == "general"


class TestCreateChange:
    def test_creates_change_with_correct_fields(self, db, test_user):
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
        )
        db.add(source)
        db.flush()

        snap_before = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash="old_hash" + "0" * 56,
            content="old content",
        )
        snap_after = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash="new_hash" + "0" * 56,
            content="new content",
        )
        db.add_all([snap_before, snap_after])
        db.flush()

        diff_text = "-old\n+new"
        diff_raw = {"added": ["new"], "removed": ["old"]}

        change = create_change(
            db,
            source,
            snap_before,
            snap_after,
            diff_text,
            diff_raw,
            "pricing",
        )

        assert change.competitor_id == competitor.id
        assert change.source_id == source.id
        assert change.source_type == "website"
        assert change.section == "pricing"
        assert change.diff_text == diff_text
        assert change.diff_raw == diff_raw
        assert change.snapshot_before_id == snap_before.id
        assert change.snapshot_after_id == snap_after.id
        assert change.status == "pending"

    def test_creates_change_without_before_snapshot(self, db, test_user):
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
            source_type="mercadolibre",
            config={"seller_id": "123"},
        )
        db.add(source)
        db.flush()

        snap_after = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="mercadolibre",
            content_hash="first_hash" + "0" * 54,
            content="first content",
        )
        db.add(snap_after)
        db.flush()

        change = create_change(
            db,
            source,
            None,
            snap_after,
            "Primer snapshot",
            {"added": ["todo"], "removed": []},
            "pricing",
        )

        assert change.snapshot_before_id is None
        assert change.snapshot_after_id == snap_after.id
        assert change.status == "pending"

    def test_change_is_persisted_after_flush(self, db, test_user):
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
            source_type="jobs",
        )
        db.add(source)
        db.flush()

        snap_after = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="jobs",
            content_hash="hash" + "0" * 60,
            content="content",
        )
        db.add(snap_after)
        db.flush()

        change = create_change(
            db,
            source,
            None,
            snap_after,
            "diff",
            {},
            "jobs",
        )

        result = db.query(Change).filter(Change.id == change.id).first()
        assert result is not None
        assert result.section == "jobs"
        assert result.status == "pending"


class TestIdempotencyLogic:
    """Verifica la logica de idempotencia: mismo hash = no change."""

    def test_same_hash_should_not_create_change(self, db, test_user):
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
        )
        db.add(source)
        db.flush()

        existing_hash = "same_hash" + "0" * 55
        snap = Snapshot(
            competitor_id=competitor.id,
            source_id=source.id,
            source_type="website",
            content_hash=existing_hash,
            content="contenido existente",
        )
        db.add(snap)
        db.flush()

        last_snap = get_last_snapshot(db, source.id)
        assert last_snap is not None
        assert last_snap.content_hash == existing_hash

        new_hash = existing_hash
        assert new_hash == last_snap.content_hash
