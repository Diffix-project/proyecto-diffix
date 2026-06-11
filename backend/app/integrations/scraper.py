"""
Integración con Playwright para scraping web.

Interfaz pública:
  fetch_clean_text(url) -> str

En modo mock devuelve texto fijo de ejemplo.
En modo real usa Playwright (API síncrona) para ejecutar JavaScript y extraer
el texto visible, luego lo limpia para que el hash sea determinista entre re-runs.
"""

import logging
import re
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """
    Fallo controlado del scraper (timeouts agotados, error de red, bloqueo anti-bot).

    El Scout captura esta excepción por fuente y continúa con las demás: un sitio
    que falla nunca detiene el monitoreo del resto.
    """


# Backoff exponencial entre reintentos: 1s, 2s, 4s, ...
_BACKOFF_BASE_SECONDS = 1.0

# Códigos HTTP típicos de bloqueo de bots / rate limiting.
_BLOCKED_STATUSES = frozenset({403, 429})

# Selectores comunes de CAPTCHA en el DOM.
_CAPTCHA_SELECTORS = (
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[title*='captcha' i]",
    "#captcha",
    ".g-recaptcha",
    ".h-captcha",
    "[data-sitekey]",
)

_MOCK_TEXT = (
    "Bienvenidos a Distribuidora Ejemplo S.A.\n"
    "Precios vigentes desde el 01/06/2026.\n"
    "Producto A: $1.200 | Producto B: $3.500 | Producto C: $800\n"
    "Nuevas condiciones de entrega: 48hs hábiles en AMBA.\n"
    "Contacto: ventas@ejemplo.com.ar"
)

# ─── Patrones de ruido dinámico (regex compilados para performance) ───────────
# El objetivo es que el hash del texto sea determinista entre re-runs: se
# eliminan líneas cuyo contenido cambia solo por el paso del tiempo (timestamps
# relativos, contadores) o que son chrome del sitio (banners de cookies).

# Timestamps relativos ES/EN. Si aparecen en cualquier parte de la línea, esa
# línea es volátil entre re-runs → se elimina entera.
_RELATIVE_TIMESTAMP_RE = re.compile(
    r"\bhace\s+(un[oa]?|\d[\d.,]*)\s+(segundo|minuto|hora|d[ií]a|semana|mes|a[ñn]o)s?\b"
    r"|\bhace\s+(un\s+momento|instantes|unos\s+segundos)\b"
    r"|\b\d[\d.,]*\s+(second|minute|hour|day|week|month|year)s?\s+ago\b"
    r"|\b(updated|posted|published|publicado|actualizado)\b[^\n]*\bago\b"
    r"|\bjust\s+now\b|\bahora\s+mismo\b",
    re.IGNORECASE,
)

# Palabras de contadores dinámicos (vistas, comentarios, compartidos, etc.).
_COUNTER_WORDS = (
    r"(?:visitas?|vistas?|reproducciones|comentarios?|compartid[oa]s?|me\s+gusta"
    r"|reacciones|seguidores|likes?|views?|comments?|shares?|reactions?|followers?)"
)
# Contadores: solo se elimina la línea si es esencialmente el contador (anclado a
# inicio/fin de línea) para no descartar contenido relevante que mencione números.
_COUNTER_RE = re.compile(
    rf"^[\d.,]+\s+{_COUNTER_WORDS}$"
    rf"|^{_COUNTER_WORDS}:?\s+[\d.,]+$"
    rf"|^(?:shared|compartido)\s+[\d.,]+\s+(?:times|veces)$",
    re.IGNORECASE,
)

# Banners de cookies / consentimiento.
_COOKIE_RE = re.compile(
    r"\bcookies?\b|\bconsentimiento\b|\bconsent\b"
    r"|\bpol[ií]tica de (cookies|privacidad)\b"
    r"|\bpreferencias de (cookies|privacidad)\b"
    r"|\bgestionar cookies\b|\bwe use cookies\b",
    re.IGNORECASE,
)


def _is_noise(line: str) -> bool:
    """True si la línea es ruido dinámico (timestamp, contador o cookie banner)."""
    return bool(
        _RELATIVE_TIMESTAMP_RE.search(line) or _COUNTER_RE.search(line) or _COOKIE_RE.search(line)
    )


def clean_scraped_text(raw_text: str) -> str:
    """
    Limpia el texto extraído para que el hash sea determinista entre re-runs.

    - Normaliza whitespace: colapsa espacios múltiples y hace trim por línea.
    - Elimina líneas de ruido dinámico (timestamps relativos, contadores) y
      banners de cookies/consentimiento.
    - Colapsa líneas vacías consecutivas.

    Es una función pura y determinista: misma entrada → misma salida.
    """
    cleaned: list[str] = []
    prev_blank = False
    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.split())
        if line and _is_noise(line):
            continue
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = is_blank

    return "\n".join(cleaned).strip()


def _has_captcha(page) -> bool:  # type: ignore[no-untyped-def]
    """Detecta elementos comunes de CAPTCHA en el DOM ya cargado."""
    return any(page.query_selector(selector) is not None for selector in _CAPTCHA_SELECTORS)


def _navigate_and_extract(url: str) -> str:
    """
    Un intento de navegación: lanza Chromium headless, navega la URL y devuelve
    el innerText del body. Detecta bloqueos anti-bot (status 403/429, CAPTCHA).

    Lanza el browser por llamada y lo cierra en finally para no dejar procesos
    de Chromium colgados. La reutilización de browser entre llamadas se evita a
    propósito: en un worker Celery prefork un browser de larga vida es frágil.

    Raises:
        ScraperError: si el sitio bloquea el scraping (HTTP 403/429 o CAPTCHA).
        PlaywrightError: si hay timeout o error de red (lo maneja el retry wrapper).
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent=settings.scraper_user_agent,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            response = page.goto(url, wait_until="networkidle", timeout=settings.scraper_timeout_ms)

            status = response.status if response is not None else None
            if status in _BLOCKED_STATUSES:
                logger.warning("scraper bloqueo anti-bot url=%s status=%s", url, status)
                raise ScraperError(f"Sitio bloqueó el scraping (HTTP {status}): {url}")

            if _has_captcha(page):
                logger.warning("scraper CAPTCHA detectado url=%s", url)
                raise ScraperError(f"CAPTCHA detectado en {url}")

            return page.inner_text("body")
        finally:
            browser.close()


def _fetch_raw_text(url: str) -> str:
    """
    Navega la URL con reintentos ante timeout/error de red (backoff exponencial).

    Los bloqueos anti-bot (ScraperError) no se reintentan: son deterministas.
    Si se agotan los intentos, lanza ScraperError (nunca crashea al worker).
    """
    total_attempts = settings.scraper_max_retries + 1
    last_error: PlaywrightError | None = None

    for attempt in range(1, total_attempts + 1):
        started = time.monotonic()
        try:
            return _navigate_and_extract(url)
        except PlaywrightError as exc:
            elapsed = time.monotonic() - started
            last_error = exc
            logger.warning(
                "scraper intento %d/%d falló url=%s (%.2fs): %s",
                attempt,
                total_attempts,
                url,
                elapsed,
                exc,
            )
            if attempt < total_attempts:
                time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    raise ScraperError(f"No se pudo scrapear {url} tras {total_attempts} intentos: {last_error}")


def fetch_clean_text(url: str) -> str:
    """
    Navega la URL con Playwright y devuelve el texto visible limpio.

    Mock: devuelve texto de ejemplo sin llamada de red.
    Real: lanza Chromium headless (con retries y detección anti-bot), extrae el
    innerText del body y lo limpia.

    Raises:
        ScraperError: ante bloqueo anti-bot o si se agotan los reintentos.
    """
    if settings.use_mocks:
        logger.debug("scraper [mock] fetch_clean_text url=%s", url)
        return _MOCK_TEXT

    logger.info("scraper fetch_clean_text url=%s", url)
    raw_text = _fetch_raw_text(url)
    return clean_scraped_text(raw_text)
