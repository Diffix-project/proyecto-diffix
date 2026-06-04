"""
Integración con Resend para envío de emails.

Interfaz pública:
  send_email(to, subject, html) -> dict

En modo mock logea y devuelve respuesta simulada.
En modo real usa la API de Resend via httpx (stub básico para fase Notificaciones).
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str) -> dict:
    """
    Envía un email via Resend.

    Mock: logea el intento y devuelve {"status": "sent", "id": "mock"}.
    Real: POST a la API de Resend con la API key configurada.
    """
    if settings.use_mocks:
        logger.info(
            "email [mock] send_email to=%s subject=%r (html len=%d)", to, subject, len(html)
        )
        return {"status": "sent", "id": "mock"}

    # Real: fase Notificaciones
    # TODO (fase Notificaciones): implementar envío real con httpx:
    #
    # import httpx
    # response = httpx.post(
    #     "https://api.resend.com/emails",
    #     headers={"Authorization": f"Bearer {settings.resend_api_key}"},
    #     json={
    #         "from": "vigi.ai <alertas@vigi.ai>",
    #         "to": [to],
    #         "subject": subject,
    #         "html": html,
    #     },
    #     timeout=10,
    # )
    # response.raise_for_status()
    # return response.json()

    raise NotImplementedError("email real mode: completar en fase Notificaciones")
