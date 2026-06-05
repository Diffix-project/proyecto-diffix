"""
Integración con la API oficial de MercadoLibre Argentina.

Interfaz pública:
  get_seller_state(seller_id) -> dict

Nunca scrapear MercadoLibre directamente; siempre usar la API oficial.

En modo mock devuelve datos de ejemplo.
En modo real usa la API oficial (stub para fase Scout).
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

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
    Real: TODO — implementar en fase Scout con la API oficial de ML.
    """
    if settings.use_mocks:
        logger.debug("mercadolibre [mock] get_seller_state seller_id=%s", seller_id)
        state = _MOCK_SELLER_STATE.copy()
        state["seller_id"] = seller_id
        return state

    # Real: fase Scout
    # TODO (fase Scout): usar la API oficial de MercadoLibre:
    #   GET https://api.mercadolibre.com/sites/MLA/search?seller_id={seller_id}
    #   GET https://api.mercadolibre.com/users/{seller_id}
    #   Autenticar con ml_client_id / ml_client_secret via OAuth2 client credentials.
    raise NotImplementedError("mercadolibre real mode: completar en fase Scout")
