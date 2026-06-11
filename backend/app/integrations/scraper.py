"""
Integración con Playwright para scraping web.

Interfaz pública:
  fetch_clean_text(url) -> str

En modo mock devuelve texto fijo de ejemplo.
En modo real usa Playwright (API síncrona) para ejecutar JavaScript y extraer
el texto visible, luego lo limpia para que el hash sea determinista entre re-runs.
"""

import logging

from playwright.sync_api import sync_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)

_MOCK_TEXT = (
    "Bienvenidos a Distribuidora Ejemplo S.A.\n"
    "Precios vigentes desde el 01/06/2026.\n"
    "Producto A: $1.200 | Producto B: $3.500 | Producto C: $800\n"
    "Nuevas condiciones de entrega: 48hs hábiles en AMBA.\n"
    "Contacto: ventas@ejemplo.com.ar"
)


def clean_scraped_text(raw_text: str) -> str:
    """
    Normaliza el texto extraído para que sea determinista.

    En esta etapa (DIX-23) sólo normaliza whitespace: colapsa espacios múltiples,
    hace trim por línea y elimina líneas vacías consecutivas. La eliminación de
    ruido dinámico (timestamps, contadores) se implementa en DIX-24 sobre este hook.
    """
    lines = [" ".join(line.split()) for line in raw_text.splitlines()]

    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = is_blank

    return "\n".join(cleaned).strip()


def _fetch_raw_text(url: str) -> str:
    """
    Navega la URL con Chromium headless y devuelve el innerText del body.

    Lanza el browser por llamada y lo cierra en finally para no dejar procesos
    de Chromium colgados. La reutilización de browser entre llamadas se evita a
    propósito: en un worker Celery prefork un browser de larga vida es frágil.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent=settings.scraper_user_agent,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=settings.scraper_timeout_ms)
            return page.inner_text("body")
        finally:
            browser.close()


def fetch_clean_text(url: str) -> str:
    """
    Navega la URL con Playwright y devuelve el texto visible limpio.

    Mock: devuelve texto de ejemplo sin llamada de red.
    Real: lanza Chromium headless, extrae el innerText del body y lo limpia.
    """
    if settings.use_mocks:
        logger.debug("scraper [mock] fetch_clean_text url=%s", url)
        return _MOCK_TEXT

    logger.info("scraper fetch_clean_text url=%s", url)
    raw_text = _fetch_raw_text(url)
    return clean_scraped_text(raw_text)
