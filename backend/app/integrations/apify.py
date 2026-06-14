"""
Integración con Apify para obtener job postings.

Interfaz pública:
  get_job_postings(company_name, since_days=30) -> list[dict]

Nunca scrapear LinkedIn directamente; siempre usar Apify.

En modo mock devuelve lista de ejemplo.
En modo real usa la API de Apify (stub para fase Scout).
"""

import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Intervalo entre cada poll del estado del run (segundos).
_POLL_INTERVAL_SECONDS = 5
# Reintentos ante rate limiting (429) antes de abortar.
_MAX_RATE_LIMIT_RETRIES = 5
# Estados terminales del run de Apify.
_RUN_STATUS_SUCCEEDED = "SUCCEEDED"
_RUN_STATUS_TERMINAL_ERRORS = {"FAILED", "ABORTED", "TIMED-OUT"}


class ApifyError(Exception):
    """Error genérico de la integración con Apify."""

    pass


class ApifyAuthError(ApifyError):
    """Error de autenticación con la API de Apify (token inválido o faltante)."""

    pass


class ApifyTimeoutError(ApifyError):
    """El run de Apify no terminó dentro del timeout configurado."""

    pass


class ApifyRunError(ApifyError):
    """El run de Apify terminó en un estado de error (FAILED/ABORTED/TIMED-OUT)."""

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


def _request(method: str, url: str, **kwargs) -> httpx.Response:
    """
    Ejecuta una request a la API de Apify con manejo de rate limiting (429).

    Reintenta hasta `_MAX_RATE_LIMIT_RETRIES` veces respetando `Retry-After`
    (o backoff exponencial si el header no está presente).

    Raises:
        ApifyError: Si el rate limit persiste tras agotar los reintentos,
            o ante un error de red.
    """
    for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
        try:
            response = httpx.request(method, url, headers=_apify_headers(), timeout=30.0, **kwargs)
        except httpx.RequestError as e:
            logger.error("apify: error de red en %s %s: %s", method, url, e)
            raise ApifyError(f"Error de red al llamar a Apify: {e}") from e

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 2**attempt))
            logger.warning("apify: rate limit (429), reintento %d en %ds", attempt + 1, retry_after)
            time.sleep(retry_after)
            continue

        return response

    raise ApifyError("apify: rate limit persistente tras agotar los reintentos")


def run_linkedin_scraper(search_queries: list[str]) -> str:
    """
    Dispara el actor de LinkedIn Jobs con las queries de búsqueda dadas.

    Args:
        search_queries: Términos de búsqueda (ej: nombres de empresas).

    Returns:
        El `run_id` del run disparado.

    Raises:
        ApifyError: Ante error de la API o de red.
    """
    actor_path = settings.apify_actor_id.replace("/", "~")
    url = f"{settings.apify_api_base_url}/acts/{actor_path}/runs"

    response = _request("POST", url, json={"searchQueries": search_queries})
    if response.status_code in (401, 403):
        raise ApifyAuthError(f"Token de Apify inválido: {response.status_code}")
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ApifyError(f"Error al disparar el actor de Apify: {e.response.status_code}") from e

    run_id = response.json()["data"]["id"]
    logger.debug("apify: run disparado run_id=%s queries=%s", run_id, search_queries)
    return run_id


def poll_run_result(run_id: str, timeout: int = 120) -> dict:
    """
    Espera a que el run de Apify termine, consultando su estado cada 5 segundos.

    Args:
        run_id: ID del run a consultar.
        timeout: Tiempo máximo de espera en segundos (default 120).

    Returns:
        Los datos del run (campo `data`) una vez en estado SUCCEEDED.

    Raises:
        ApifyTimeoutError: Si el run no termina dentro de `timeout`.
        ApifyRunError: Si el run termina en FAILED/ABORTED/TIMED-OUT.
        ApifyError: Ante error de la API o de red.
    """
    url = f"{settings.apify_api_base_url}/acts/runs/{run_id}"
    deadline = time.monotonic() + timeout

    while True:
        response = _request("GET", url)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ApifyError(f"Error al consultar el run {run_id}: {e.response.status_code}") from e

        data = response.json()["data"]
        status = data.get("status")

        if status == _RUN_STATUS_SUCCEEDED:
            logger.debug("apify: run %s SUCCEEDED", run_id)
            return data

        if status in _RUN_STATUS_TERMINAL_ERRORS:
            raise ApifyRunError(f"El run {run_id} terminó en estado {status}")

        if time.monotonic() >= deadline:
            raise ApifyTimeoutError(
                f"El run {run_id} no terminó en {timeout}s (último estado: {status})"
            )

        time.sleep(_POLL_INTERVAL_SECONDS)


def get_dataset_items(run_id: str) -> list[dict]:
    """
    Obtiene los items del dataset producido por un run.

    Args:
        run_id: ID del run cuyo dataset se quiere leer.

    Returns:
        Lista de items del dataset.

    Raises:
        ApifyError: Ante error de la API o de red.
    """
    url = f"{settings.apify_api_base_url}/acts/runs/{run_id}/dataset/items"
    response = _request("GET", url)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ApifyError(
            f"Error al obtener el dataset del run {run_id}: {e.response.status_code}"
        ) from e

    items = response.json()
    logger.debug("apify: %d items obtenidos del run %s", len(items), run_id)
    return items


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
