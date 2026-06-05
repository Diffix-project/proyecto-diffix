"""
Integración con Playwright para scraping web.

Interfaz pública:
  fetch_clean_text(url) -> str

En modo mock devuelve texto fijo de ejemplo.
En modo real usa Playwright para ejecutar JavaScript y extraer texto visible limpio.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_MOCK_TEXT = (
    "Bienvenidos a Distribuidora Ejemplo S.A.\n"
    "Precios vigentes desde el 01/06/2026.\n"
    "Producto A: $1.200 | Producto B: $3.500 | Producto C: $800\n"
    "Nuevas condiciones de entrega: 48hs hábiles en AMBA.\n"
    "Contacto: ventas@ejemplo.com.ar"
)


def fetch_clean_text(url: str) -> str:
    """
    Navega la URL con Playwright y devuelve el texto visible limpio.

    Mock: devuelve texto de ejemplo sin llamada de red.
    Real: TODO — implementar en fase Scout con Playwright.
    """
    if settings.use_mocks:
        logger.debug("scraper [mock] fetch_clean_text url=%s", url)
        return _MOCK_TEXT

    # Real: fase Scout
    # TODO (fase Scout): usar Playwright para:
    #   1. Lanzar browser (chromium headless)
    #   2. Navegar a la URL con timeout razonable
    #   3. Esperar hidratación JS (networkidle o selector clave)
    #   4. Extraer innerText del body, filtrar ruido (fechas, contadores)
    #   5. Cerrar browser
    raise NotImplementedError("scraper real mode: completar en fase Scout")
