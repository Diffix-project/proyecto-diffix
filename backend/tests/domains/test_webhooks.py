"""
Tests de webhooks para auth y billing.

Cobertura:
- POST /auth/webhook con user.created crea el User en la DB.
- POST /billing/webhook con status=approved actualiza el plan del usuario.
"""

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

AUTH_WEBHOOK_URL = "/api/v1/auth/webhook"
BILLING_WEBHOOK_URL = "/api/v1/billing/webhook"


class TestAuthWebhook:
    def test_user_created_event_creates_user(self, client: TestClient, db: Session):
        """
        POST /auth/webhook con type=user.created debe hacer upsert del usuario
        y el usuario debe existir en la DB.
        """
        from app.domains.auth.models import User

        payload = {
            "type": "user.created",
            "data": {
                "id": "clerk_webhook_test_001",
                "email_addresses": [{"email_address": "webhook@test.com"}],
                "first_name": "Juan",
                "last_name": "Webhook",
            },
        }

        r = client.post(
            AUTH_WEBHOOK_URL,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        assert r.json() == {"received": True}

        # Verificar que el usuario fue creado en DB
        user = db.query(User).filter(User.clerk_id == "clerk_webhook_test_001").first()
        assert user is not None
        assert user.email == "webhook@test.com"
        assert user.name == "Juan Webhook"

    def test_unknown_event_type_ignored(self, client: TestClient, db: Session):
        """Tipos de evento desconocidos no deben fallar, solo devolver received=True."""
        payload = {"type": "user.deleted", "data": {"id": "clerk_xyz"}}
        r = client.post(
            AUTH_WEBHOOK_URL,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        assert r.json() == {"received": True}


class TestBillingWebhook:
    def test_approved_payment_updates_plan(self, client: TestClient, db: Session):
        """
        POST /billing/webhook con status=approved debe actualizar el plan del usuario.
        """
        from app.domains.auth.service import upsert_user_from_clerk

        # Crear el usuario que recibirá el upgrade
        user = upsert_user_from_clerk(
            db, clerk_id="clerk_billing_test", email="billing@test.com", name="Billing User"
        )
        assert user.plan == "free"

        payload = {
            "status": "approved",
            "user_clerk_id": "clerk_billing_test",
            "plan": "starter",
        }

        r = client.post(
            BILLING_WEBHOOK_URL,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200

        # Verificar que el plan fue actualizado
        db.expire_all()
        db.refresh(user)
        assert user.plan == "starter"

    def test_non_approved_payment_ignored(self, client: TestClient, db: Session):
        """Pagos con status != approved no deben cambiar el plan."""
        from app.domains.auth.service import upsert_user_from_clerk

        user = upsert_user_from_clerk(
            db, clerk_id="clerk_billing_pending", email="pending@test.com", name="Pending User"
        )

        payload = {
            "status": "pending",
            "user_clerk_id": "clerk_billing_pending",
            "plan": "growth",
        }

        r = client.post(
            BILLING_WEBHOOK_URL,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200

        db.expire_all()
        db.refresh(user)
        # Plan no debe cambiar
        assert user.plan == "free"
