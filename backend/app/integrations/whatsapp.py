"""
Integración con Twilio WhatsApp Business API.

Interfaz pública:
  send_whatsapp(to, body) -> dict

En modo mock logea y devuelve respuesta simulada.
En modo real usa el SDK de Twilio (stub para fase Notificaciones).
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_whatsapp(to: str, body: str) -> dict:
    """
    Envía un mensaje de WhatsApp via Twilio.

    `to` debe incluir el prefijo 'whatsapp:+549...' o solo el número;
    el caller es responsable del formato correcto.

    Mock: logea el intento y devuelve {"status": "sent", "sid": "mock"}.
    Real: TODO — implementar en fase Notificaciones con el SDK de Twilio.
    """
    if settings.use_mocks:
        logger.info("whatsapp [mock] send_whatsapp to=%s body=%r", to, body[:80])
        return {"status": "sent", "sid": "mock"}

    # Real: fase Notificaciones
    # TODO (fase Notificaciones): usar el SDK de Twilio:
    #
    # from twilio.rest import Client
    # client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    # message = client.messages.create(
    #     from_=settings.twilio_whatsapp_from,
    #     to=to if to.startswith("whatsapp:") else f"whatsapp:{to}",
    #     body=body,
    # )
    # return {"status": message.status, "sid": message.sid}

    raise NotImplementedError("whatsapp real mode: completar en fase Notificaciones")
