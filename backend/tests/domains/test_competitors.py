"""
Tests de integración para el dominio competitors.

Cobertura:
- Límite de plan: free permite 2, el 3° devuelve 403 plan_limit_reached.
- Upgrade de plan permite crear más competidores.
- Soft delete: DELETE deja is_active=False; GET list no lo devuelve; sigue en DB.
- Scoping: competidor de otra company devuelve 404.
- Validación de schema: nombre vacío → 422.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import make_competitor

COMPETITOR_URL = "/api/v1/competitors"

VALID_PAYLOAD = {
    "name": "Competidor Test",
    "website_url": "https://competidor.com",
    "sources": [],
}


class TestPlanLimit:
    def test_free_allows_two_competitors(self, client: TestClient, test_user):
        """Plan free: crear 2 competidores debe devolver 201."""
        r1 = client.post(COMPETITOR_URL, json={**VALID_PAYLOAD, "name": "Comp 1"})
        assert r1.status_code == 201, r1.text

        r2 = client.post(COMPETITOR_URL, json={**VALID_PAYLOAD, "name": "Comp 2"})
        assert r2.status_code == 201, r2.text

    def test_free_third_competitor_blocked(self, client: TestClient, test_user, db: Session):
        """Plan free: el 3° competidor devuelve 403 con code=plan_limit_reached."""
        # Crear los 2 permitidos directo en DB para aislar el test
        make_competitor(db, test_user.company, "Bloqueado 1")
        make_competitor(db, test_user.company, "Bloqueado 2")

        r = client.post(COMPETITOR_URL, json={**VALID_PAYLOAD, "name": "Bloqueado 3"})
        assert r.status_code == 403
        body = r.json()
        assert body["code"] == "plan_limit_reached"

    def test_growth_plan_allows_more(self, client: TestClient, test_user, db: Session):
        """Después de upgrade a growth (límite 10): crear 3 competidores debe funcionar."""
        # Upgradear el plan del usuario mock actual a growth
        test_user.plan = "growth"
        db.commit()
        db.refresh(test_user)

        for i in range(3):
            r = client.post(COMPETITOR_URL, json={**VALID_PAYLOAD, "name": f"Growth Comp {i}"})
            assert r.status_code == 201, r.text


class TestSoftDelete:
    def test_delete_sets_inactive(self, client: TestClient, test_user, db: Session):
        """DELETE /competitors/:id deja is_active=False en la DB."""
        from app.domains.competitors.models import Competitor

        comp = make_competitor(db, test_user.company, "Para Borrar")
        comp_id = str(comp.id)

        r = client.delete(f"{COMPETITOR_URL}/{comp_id}")
        assert r.status_code == 204

        # Verificar directo en DB que is_active es False
        db.expire_all()
        db_comp = db.query(Competitor).filter(Competitor.id == comp.id).first()
        assert db_comp is not None, "El registro debe seguir en la DB"
        assert db_comp.is_active is False

    def test_deleted_not_in_list(self, client: TestClient, test_user, db: Session):
        """GET /competitors no incluye el competidor borrado."""
        comp = make_competitor(db, test_user.company, "Invisible")
        comp_id = str(comp.id)

        client.delete(f"{COMPETITOR_URL}/{comp_id}")

        r = client.get(COMPETITOR_URL)
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()]
        assert comp_id not in ids

    def test_deleted_not_accessible_by_id(self, client: TestClient, test_user, db: Session):
        """GET /competitors/:id de un competidor borrado devuelve 404."""
        comp = make_competitor(db, test_user.company, "Fantasma")
        comp_id = str(comp.id)

        client.delete(f"{COMPETITOR_URL}/{comp_id}")

        r = client.get(f"{COMPETITOR_URL}/{comp_id}")
        assert r.status_code == 404


class TestScoping:
    def test_other_company_competitor_returns_404(self, client: TestClient, db: Session):
        """
        Un competidor de otra company no es accesible por el usuario actual.

        Creamos otro usuario+company manualmente en la DB y verificamos
        que GET /competitors/:id devuelve 404 para el usuario mock actual.
        """
        from app.domains.auth.service import upsert_user_from_clerk

        # Crear otra empresa con un competidor
        other_user = upsert_user_from_clerk(
            db, clerk_id="other_clerk_user", email="other@vigi.ai", name="Other"
        )
        other_comp = make_competitor(db, other_user.company, "Competidor Ajeno")

        r = client.get(f"{COMPETITOR_URL}/{other_comp.id}")
        assert r.status_code == 404


class TestSchemaValidation:
    def test_missing_name_returns_422(self, client: TestClient, test_user):
        """Crear competidor sin name devuelve 422."""
        r = client.post(COMPETITOR_URL, json={"website_url": "https://x.com"})
        assert r.status_code == 422

    def test_missing_website_url_returns_422(self, client: TestClient, test_user):
        """Crear competidor sin website_url devuelve 422."""
        r = client.post(COMPETITOR_URL, json={"name": "Sin URL"})
        assert r.status_code == 422

    def test_invalid_source_type_returns_422(self, client: TestClient, test_user):
        """source_type inválido devuelve 422 (no 500 por IntegrityError de la DB)."""
        payload = {
            "name": "Con Fuente Invalida",
            "website_url": "https://x.com",
            "sources": [{"source_type": "facebook", "source_url": "https://x.com"}],
        }
        r = client.post(COMPETITOR_URL, json=payload)
        assert r.status_code == 422

    def test_add_source_invalid_type_returns_422(self, client: TestClient, test_user, db: Session):
        """POST de una fuente con source_type inválido devuelve 422."""
        comp = make_competitor(db, test_user.company, "Para Fuente")
        r = client.post(
            f"{COMPETITOR_URL}/{comp.id}/sources",
            json={"source_type": "instagram", "source_url": "https://x.com"},
        )
        assert r.status_code == 422
