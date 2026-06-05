"""
Seguridad: autenticación JWT de Clerk y verificación de webhooks.

En modo USE_MOCKS=true:
  - get_current_user devuelve un usuario mock sin validar JWT.
  - verify_clerk_webhook parsea el JSON sin verificar firma svix.

En modo real:
  - get_current_user obtiene las claves JWKS de Clerk y valida el Bearer token.
  - verify_clerk_webhook verifica la firma con svix y CLERK_WEBHOOK_SECRET.
"""

import json
import logging
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Cache en memoria para las claves JWKS (se refresca cada proceso)
_jwks_cache: dict[str, Any] | None = None


async def _get_jwks() -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.clerk_jwks_url, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


# ─── Tipo del usuario autenticado ────────────────────────────────────────────


class AuthUser:
    """Datos del usuario autenticado extraídos del JWT de Clerk."""

    def __init__(self, clerk_id: str, email: str = "") -> None:
        self.clerk_id = clerk_id
        self.email = email


MOCK_USER = AuthUser(clerk_id="mock_clerk_user", email="dev@vigi.ai")


# ─── Dependency de autenticación ─────────────────────────────────────────────


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUser:
    """
    Dependency FastAPI que retorna el usuario autenticado.

    - USE_MOCKS=true: retorna MOCK_USER sin validar token (útil para dev/tests).
    - USE_MOCKS=false: valida el JWT Bearer de Clerk contra el JWKS.

    El agente C (dominios) usa este dependency para resolver el User de la DB
    a partir de clerk_id.
    """
    if settings.use_mocks:
        return MOCK_USER

    if credentials is None:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido")

    token = credentials.credentials
    try:
        await _get_jwks()
        # PyJWT soporta JWKS directamente desde la versión 2.4
        signing_keys = jwt.PyJWKClient(settings.clerk_jwks_url)
        signing_key = signing_keys.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        clerk_id: str = payload.get("sub", "")
        email: str = payload.get("email", "")
        return AuthUser(clerk_id=clerk_id, email=email)
    except Exception as exc:
        logger.warning("JWT inválido: %s", exc)
        raise HTTPException(status_code=401, detail="Token inválido o expirado") from exc


# ─── Verificación de webhook Clerk ───────────────────────────────────────────


def verify_clerk_webhook(payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """
    Verifica la firma del webhook de Clerk usando svix.

    - USE_MOCKS=true: parsea el JSON sin verificar firma.
    - USE_MOCKS=false: verifica con CLERK_WEBHOOK_SECRET y svix.

    Lanza HTTPException 400 si la verificación falla.
    """
    if settings.use_mocks:
        return json.loads(payload)  # type: ignore[no-any-return]

    try:
        from svix.webhooks import Webhook

        wh = Webhook(settings.clerk_webhook_secret)
        return wh.verify(payload, headers)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("Firma de webhook Clerk inválida: %s", exc)
        raise HTTPException(status_code=400, detail="Firma de webhook inválida") from exc


# ─── Stub: verificación de webhook Mercado Pago ──────────────────────────────


def verify_mp_webhook(payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """
    Verifica la firma del webhook de Mercado Pago.

    Stub — el agente C completará la implementación real con
    la firma HMAC-SHA256 usando MP_WEBHOOK_SECRET.
    """
    if settings.use_mocks:
        return json.loads(payload)  # type: ignore[no-any-return]

    # TODO (agente C): implementar verificación HMAC-SHA256 de MP
    # Ver: https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks
    raise NotImplementedError("verify_mp_webhook no implementado en modo real")
