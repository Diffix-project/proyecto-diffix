"""
Integración con Apify para obtener job postings.

Interfaz pública:
  get_job_postings(company_name, since_days=30) -> list[dict]

Nunca scrapear LinkedIn directamente; siempre usar Apify.

En modo mock devuelve lista de ejemplo.
En modo real usa la API de Apify (stub para fase Scout).
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyError(Exception):
    """Error genérico de la integración con Apify."""

    pass


class ApifyAuthError(ApifyError):
    """Error de autenticación con la API de Apify (token inválido o faltante)."""

    pass


def _apify_headers() -> dict:
    """
    Retorna headers de autenticación para la API de Apify.

    Raises:
        ApifyAuthError: Si no hay token configurado.
    """
    if not settings.apify_token:
        raise ApifyAuthError(
            "apify_token es requerido. Configurar APIFY_TOKEN en .env "
            "o usar USE_MOCKS=true para desarrollo local."
        )
    return {
        "Authorization": f"Bearer {settings.apify_token}",
        "Accept": "application/json",
    }


def verify_token() -> dict:
    """
    Verifica que el token de Apify es válido con un call a GET /v2/users/me.

    Returns:
        Datos del usuario autenticado (campo `data` del response).

    Raises:
        ApifyAuthError: Si el token es inválido (401/403) o falta.
        ApifyError: Ante otros errores de la API o de red.
    """
    url = f"{settings.apify_api_base_url}/users/me"
    try:
        response = httpx.get(url, headers=_apify_headers(), timeout=30.0)

        if response.status_code in (401, 403):
            raise ApifyAuthError(f"Token de Apify inválido: {response.status_code}")

        response.raise_for_status()
        data = response.json().get("data", {})
        logger.debug("apify: token verificado, usuario=%s", data.get("username"))
        return data

    except httpx.HTTPStatusError as e:
        logger.error(
            "apify: error al verificar token status=%d response=%s",
            e.response.status_code,
            e.response.text,
        )
        raise ApifyError(f"Error al verificar token de Apify: {e.response.status_code}") from e
    except httpx.RequestError as e:
        logger.error("apify: error de red al verificar token: %s", e)
        raise ApifyError(f"Error de red al verificar token: {e}") from e


_MOCK_JOB_POSTINGS: list[dict] = [
    {
        "title": "Desarrollador Backend Python",
        "company": "Empresa Ejemplo",
        "location": "Buenos Aires, AR",
        "posted_at": "2026-05-28",
        "url": "https://www.linkedin.com/jobs/view/mock-1",
        "description": "Buscamos desarrollador Python con experiencia en FastAPI y PostgreSQL.",
    },
    {
        "title": "Jefe de Ventas Zona Norte",
        "company": "Empresa Ejemplo",
        "location": "Buenos Aires, AR",
        "posted_at": "2026-05-30",
        "url": "https://www.linkedin.com/jobs/view/mock-2",
        "description": "Responsable de expandir cartera de clientes en zona norte GBA.",
    },
]


def get_job_postings(company_name: str, since_days: int = 30) -> list[dict]:
    """
    Devuelve publicaciones de empleo de la empresa en los últimos `since_days` días.

    Mock: lista de ejemplo sin llamada de red.
    Real: TODO — implementar en fase Scout usando el actor de Apify para LinkedIn Jobs.
    """
    if settings.use_mocks:
        logger.debug(
            "apify [mock] get_job_postings company=%s since_days=%d", company_name, since_days
        )
        return [dict(p, company=company_name) for p in _MOCK_JOB_POSTINGS]

    # Real: fase Scout
    # TODO (fase Scout): llamar a la API de Apify:
    #   POST https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_TOKEN}
    #   Actor recomendado: apify/linkedin-jobs-scraper
    #   Filtrar resultados por fecha >= now() - since_days
    raise NotImplementedError("apify real mode: completar en fase Scout")
