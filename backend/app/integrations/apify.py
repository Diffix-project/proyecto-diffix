"""
Integración con Apify para obtener job postings.

Interfaz pública:
  get_job_postings(company_name, since_days=30) -> list[dict]

Nunca scrapear LinkedIn directamente; siempre usar Apify.

En modo mock devuelve lista de ejemplo.
En modo real usa la API de Apify (stub para fase Scout).
"""

import logging
import re
import time
from datetime import UTC, datetime, timedelta

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
# Campos donde Apify puede traer la fecha de publicación, en orden de prioridad.
_POSTED_DATE_FIELDS = ("postedDate", "postedAt", "createdAt")
# Unidades de tiempo para fechas relativas ("3 days ago").
_RELATIVE_UNIT_DAYS = {
    "hour": 0,
    "hora": 0,
    "minute": 0,
    "minuto": 0,
    "day": 1,
    "dia": 1,
    "día": 1,
    "week": 7,
    "semana": 7,
    "month": 30,
    "mes": 30,
}


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


def _parse_posting_date(value) -> datetime | None:
    """
    Parsea una fecha de publicación a datetime timezone-aware (UTC).

    Soporta ISO 8601 (con o sin 'Z') y fechas relativas en inglés/español
    ("3 days ago", "hace 2 semanas", "today", "yesterday").

    Returns:
        datetime en UTC, o None si no se puede parsear.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    text = str(value).strip().lower()
    now = datetime.now(UTC)

    if text in ("today", "hoy"):
        return now
    if text in ("yesterday", "ayer"):
        return now - timedelta(days=1)

    # Relativo: "3 days ago", "hace 2 semanas", "1 month ago".
    match = re.search(r"(\d+)\s*(hour|hora|minute|minuto|day|d[ií]a|week|semana|month|mes)", text)
    if match:
        amount = int(match.group(1))
        unit_days = _RELATIVE_UNIT_DAYS.get(match.group(2), None)
        if unit_days is not None:
            return now - timedelta(days=amount * unit_days)

    # ISO 8601.
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _raw_posted_date(item: dict):
    """Devuelve el primer campo de fecha disponible del item de Apify."""
    for field in _POSTED_DATE_FIELDS:
        if item.get(field):
            return item[field]
    return None


def filter_postings_by_date(items: list[dict], since_days: int) -> list[dict]:
    """
    Filtra postings publicados en los últimos `since_days` días.

    Los postings sin fecha parseable se descartan con un warning.
    """
    cutoff = datetime.now(UTC) - timedelta(days=since_days)
    filtered: list[dict] = []

    for item in items:
        posted = _parse_posting_date(_raw_posted_date(item))
        if posted is None:
            logger.warning(
                "apify: posting sin fecha parseable, descartado: %s",
                item.get("title") or item.get("url") or "<sin título>",
            )
            continue
        if posted >= cutoff:
            filtered.append(item)

    logger.debug("apify: %d/%d postings dentro de %d días", len(filtered), len(items), since_days)
    return filtered


def normalize_job_posting(item: dict) -> dict:
    """
    Normaliza un item de Apify al shape interno usado por JobsStrategy.

    Mapea los nombres de campos de Apify a los nombres internos, con
    fallbacks para las variaciones más comunes del actor.
    """
    return {
        "title": item.get("title"),
        "company": item.get("companyName") or item.get("company"),
        "location": item.get("location"),
        "description": item.get("description"),
        "posted_at": _raw_posted_date(item),
        "url": item.get("jobUrl") or item.get("url") or item.get("link"),
        "seniority_level": item.get("seniorityLevel") or item.get("experienceLevel"),
    }


_MOCK_JOB_POSTINGS: list[dict] = [
    {
        "title": "Desarrollador Backend Python",
        "company": "Empresa Ejemplo",
        "location": "Buenos Aires, AR",
        "posted_at": "2026-05-28",
        "url": "https://www.linkedin.com/jobs/view/mock-1",
        "description": "Buscamos desarrollador Python con experiencia en FastAPI y PostgreSQL.",
        "seniority_level": "Mid-Senior level",
    },
    {
        "title": "Jefe de Ventas Zona Norte",
        "company": "Empresa Ejemplo",
        "location": "Buenos Aires, AR",
        "posted_at": "2026-05-30",
        "url": "https://www.linkedin.com/jobs/view/mock-2",
        "description": "Responsable de expandir cartera de clientes en zona norte GBA.",
        "seniority_level": "Director",
    },
]


def get_job_postings(company_name: str, since_days: int = 30) -> list[dict]:
    """
    Devuelve publicaciones de empleo de la empresa en los últimos `since_days` días.

    Mock: lista de ejemplo sin llamada de red (`USE_MOCKS=true`).
    Real: ejecuta el actor de LinkedIn Jobs en Apify, espera el resultado,
    filtra por fecha y normaliza al shape interno.

    Raises:
        ApifyError (y subclases): ante errores de la API, timeout o run fallido.
    """
    if settings.use_mocks:
        logger.debug(
            "apify [mock] get_job_postings company=%s since_days=%d", company_name, since_days
        )
        return [dict(p, company=company_name) for p in _MOCK_JOB_POSTINGS]

    logger.debug("apify get_job_postings company=%s since_days=%d", company_name, since_days)
    run_id = run_linkedin_scraper([company_name])
    poll_run_result(run_id)
    items = get_dataset_items(run_id)
    filtered = filter_postings_by_date(items, since_days)
    return [normalize_job_posting(item) for item in filtered]
