"""
Integración con la API oficial de MercadoLibre Argentina.

Interfaz pública:
  get_seller_state(seller_id) -> dict

Nunca scrapear MercadoLibre directamente; siempre usar la API oficial.

En modo mock devuelve datos de ejemplo.
En modo real usa la API oficial con OAuth2 client credentials.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MercadoLibreAuthError(Exception):
    """Error de autenticación con la API de MercadoLibre."""

    pass


class MercadoLibreAPIError(Exception):
    """Error de la API de MercadoLibre."""

    pass


_token_cache: dict = {"access_token": None, "expires_at": 0.0}


def get_access_token() -> str:
    """
    Obtiene un access token de MercadoLibre usando OAuth2 client credentials.

    El token se cachea hasta su expiración.
    """
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    if not settings.ml_client_id or not settings.ml_client_secret:
        raise MercadoLibreAuthError(
            "ml_client_id y ml_client_secret son requeridos. "
            "Configurar en .env o usar USE_MOCKS=true para desarrollo."
        )

    url = f"{settings.ml_api_base_url}/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": settings.ml_client_id,
        "client_secret": settings.ml_client_secret,
    }

    try:
        response = httpx.post(url, data=payload, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        access_token = data["access_token"]
        expires_in = data.get("expires_in", 21600)
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = time.time() + expires_in - 60

        logger.debug("mercadolibre: token obtenido, expira en %ds", expires_in)
        return access_token

    except httpx.HTTPStatusError as e:
        logger.error(
            "mercadolibre: error de autenticación status=%d response=%s",
            e.response.status_code,
            e.response.text,
        )
        raise MercadoLibreAuthError(
            f"Error de autenticación con MercadoLibre: {e.response.status_code}"
        ) from e
    except httpx.RequestError as e:
        logger.error("mercadolibre: error de red al obtener token: %s", e)
        raise MercadoLibreAuthError(f"Error de red al obtener token: {e}") from e


def _headers() -> dict:
    """Retorna headers con Authorization Bearer token."""
    token = get_access_token()
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def get_seller_listings(seller_id: str, max_listings: int = 200) -> list[dict]:
    """
    Obtiene los listings activos de un vendedor en MercadoLibre.

    Args:
        seller_id: ID del vendedor en MercadoLibre
        max_listings: Máximo de listings a retornar (default 200)

    Returns:
        Lista de listings con campos: id, title, price, permalink, thumbnail, last_updated
        Ordenada por last_updated DESC

    Raises:
        MercadoLibreAPIError: Si el seller no existe (404) o error de API
    """
    url = f"{settings.ml_api_base_url}/sites/MLA/search"
    listings: list[dict] = []
    offset = 0
    limit = 50

    while len(listings) < max_listings:
        params: dict[str, str | int] = {
            "seller_id": seller_id,
            "status": "active",
            "offset": offset,
            "limit": limit,
        }

        try:
            response = httpx.get(
                url, params=params, headers=_headers(), timeout=30.0
            )

            if response.status_code == 404:
                raise MercadoLibreAPIError(
                    f"Seller no encontrado: {seller_id}"
                )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(
                    "mercadolibre: rate limit, esperando %ds", retry_after
                )
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            for item in results:
                listing = {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "price": item.get("price"),
                    "permalink": item.get("permalink"),
                    "thumbnail": item.get("thumbnail"),
                    "last_updated": item.get("last_updated"),
                }
                listings.append(listing)

                if len(listings) >= max_listings:
                    break

            offset += limit

            if len(results) < limit:
                break

        except httpx.RequestError as e:
            logger.error(
                "mercadolibre: error de red al obtener listings: %s", e
            )
            raise MercadoLibreAPIError(f"Error de red: {e}") from e

    listings.sort(key=lambda x: x.get("last_updated") or "", reverse=True)

    logger.debug(
        "mercadolibre: %d listings obtenidos para seller %s",
        len(listings),
        seller_id,
    )
    return listings


def get_seller_reputation(seller_id: str) -> dict:
    """
    Obtiene la reputación y estado de un vendedor en MercadoLibre.

    Args:
        seller_id: ID del vendedor en MercadoLibre

    Returns:
        Dict con: nickname, level_id, transactions_total, site_status

    Raises:
        MercadoLibreAPIError: Si el seller no existe (404) o error de API
    """
    url = f"{settings.ml_api_base_url}/users/{seller_id}"

    try:
        response = httpx.get(url, headers=_headers(), timeout=30.0)

        if response.status_code == 404:
            raise MercadoLibreAPIError(f"Seller no encontrado: {seller_id}")

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(
                "mercadolibre: rate limit en reputación, esperando %ds", retry_after
            )
            time.sleep(retry_after)
            return get_seller_reputation(seller_id)

        response.raise_for_status()
        data = response.json()

        reputation_data = data.get("seller_reputation", {})
        metrics = reputation_data.get("metrics", {})

        result = {
            "nickname": data.get("nickname"),
            "level_id": reputation_data.get("level_id"),
            "transactions_total": metrics.get("transactions_total"),
            "site_status": data.get("status", {}).get("site_status"),
        }

        logger.debug(
            "mercadolibre: reputación obtenida para seller %s: %s",
            seller_id,
            result.get("level_id"),
        )
        return result

    except httpx.RequestError as e:
        logger.error(
            "mercadolibre: error de red al obtener reputación: %s", e
        )
        raise MercadoLibreAPIError(f"Error de red: {e}") from e

_MOCK_SELLER_STATE: dict = {
    "seller_id": "mock_seller",
    "reputation": {
        "level_id": "5_green",
        "power_seller_status": "platinum",
        "transactions": {"completed": 1240, "canceled": 12},
    },
    "active_listings": 87,
    "top_products": [
        {"title": "Producto Ejemplo A", "price": 15000.0, "currency": "ARS"},
        {"title": "Producto Ejemplo B", "price": 8500.0, "currency": "ARS"},
        {"title": "Producto Ejemplo C", "price": 3200.0, "currency": "ARS"},
    ],
}


def get_seller_state(seller_id: str) -> dict:
    """
    Devuelve reputación, cantidad de publicaciones activas y precios top del vendedor.

    Mock: dict de ejemplo sin llamada de red.
    Real: combina listings + reputation en paralelo usando la API oficial de ML.
    """
    if settings.use_mocks:
        logger.debug("mercadolibre [mock] get_seller_state seller_id=%s", seller_id)
        state = _MOCK_SELLER_STATE.copy()
        state["seller_id"] = seller_id
        return state

    listings: list[dict] = []
    reputation: dict = {}
    listings_error = None
    reputation_error = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures: dict = {
            executor.submit(get_seller_listings, seller_id): "listings",
            executor.submit(get_seller_reputation, seller_id): "reputation",
        }

        for future in as_completed(futures):
            task_name = futures[future]
            try:
                result = future.result()
                if task_name == "listings":
                    listings = result
                else:
                    reputation = result
            except MercadoLibreAPIError as e:
                logger.error(
                    "mercadolibre: error en %s para seller %s: %s",
                    task_name,
                    seller_id,
                    e,
                )
                if task_name == "listings":
                    listings_error = str(e)
                else:
                    reputation_error = str(e)

    if listings_error and reputation_error:
        raise MercadoLibreAPIError(
            f"Error al obtener datos del seller {seller_id}: "
            f"listings={listings_error}, reputation={reputation_error}"
        )

    top_products = [
        {"title": listing["title"], "price": listing["price"], "currency": "ARS"}
        for listing in listings[:3]
    ]

    state = {
        "seller_id": seller_id,
        "nickname": reputation.get("nickname"),
        "reputation": {
            "level_id": reputation.get("level_id"),
            "power_seller_status": None,
            "transactions": {
                "completed": reputation.get("transactions_total") or 0,
                "canceled": 0,
            },
        },
        "active_listings": len(listings),
        "top_products": top_products,
        "status": reputation.get("site_status"),
        "total_transactions": reputation.get("transactions_total"),
        "listings": listings,
    }

    if listings_error:
        state["listings_error"] = listings_error
    if reputation_error:
        state["reputation_error"] = reputation_error

    logger.debug(
        "mercadolibre: estado completo para seller %s: %d listings, reputation=%s",
        seller_id,
        len(listings),
        reputation.get("level_id"),
    )
    return state
