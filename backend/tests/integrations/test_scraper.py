"""
Tests del scraper Playwright (DIX-23).

Cubre la implementación de fetch_clean_text con la API síncrona de Playwright:
- modo mock no instancia Playwright
- ruta real navega la URL y devuelve el innerText limpio
- el browser se cierra siempre (incluso ante error)
- normalización básica de whitespace en clean_scraped_text

Playwright se mockea por completo: los tests no abren un browser ni tocan la red.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.integrations import scraper
from app.integrations.scraper import clean_scraped_text, fetch_clean_text


def _build_playwright_mock(inner_text: str = "texto del body", *, goto_side_effect=None):
    """Arma el árbol de mocks que devuelve sync_playwright() como context manager."""
    page = MagicMock(name="page")
    page.inner_text.return_value = inner_text
    if goto_side_effect is not None:
        page.goto.side_effect = goto_side_effect

    context = MagicMock(name="context")
    context.new_page.return_value = page

    browser = MagicMock(name="browser")
    browser.new_context.return_value = context

    pw = MagicMock(name="playwright")
    pw.chromium.launch.return_value = browser

    cm = MagicMock(name="sync_playwright")
    cm.return_value.__enter__.return_value = pw
    cm.return_value.__exit__.return_value = False

    return cm, browser, context, page


@pytest.fixture()
def real_mode():
    """Fuerza settings.use_mocks=False sólo durante el test."""
    with patch.object(settings, "use_mocks", False):
        yield


class TestMockMode:
    def test_returns_mock_text(self):
        result = fetch_clean_text("https://ejemplo.com")
        assert "Distribuidora Ejemplo" in result

    def test_does_not_instantiate_playwright(self):
        with patch.object(scraper, "sync_playwright") as mock_sp:
            fetch_clean_text("https://ejemplo.com")
        mock_sp.assert_not_called()


class TestRealMode:
    def test_navigates_and_returns_inner_text(self, real_mode):
        cm, browser, _context, page = _build_playwright_mock("Producto A: $100")
        with patch.object(scraper, "sync_playwright", cm):
            result = fetch_clean_text("https://competidor.com")

        assert result == "Producto A: $100"
        page.goto.assert_called_once()
        args, kwargs = page.goto.call_args
        assert args[0] == "https://competidor.com"
        assert kwargs["wait_until"] == "networkidle"
        assert kwargs["timeout"] == settings.scraper_timeout_ms

    def test_uses_realistic_user_agent_and_viewport(self, real_mode):
        cm, browser, _context, _page = _build_playwright_mock()
        with patch.object(scraper, "sync_playwright", cm):
            fetch_clean_text("https://competidor.com")

        _args, kwargs = browser.new_context.call_args
        assert kwargs["user_agent"] == settings.scraper_user_agent
        assert kwargs["viewport"] == {"width": 1280, "height": 800}

    def test_closes_browser_on_success(self, real_mode):
        cm, browser, _context, _page = _build_playwright_mock()
        with patch.object(scraper, "sync_playwright", cm):
            fetch_clean_text("https://competidor.com")
        browser.close.assert_called_once()

    def test_closes_browser_even_if_goto_raises(self, real_mode):
        cm, browser, _context, _page = _build_playwright_mock(goto_side_effect=RuntimeError("boom"))
        with patch.object(scraper, "sync_playwright", cm):
            with pytest.raises(RuntimeError, match="boom"):
                fetch_clean_text("https://competidor.com")
        browser.close.assert_called_once()

    def test_output_is_cleaned(self, real_mode):
        cm, *_ = _build_playwright_mock("  Producto   A   \n\n\n  Producto B  ")
        with patch.object(scraper, "sync_playwright", cm):
            result = fetch_clean_text("https://competidor.com")
        assert result == "Producto A\n\nProducto B"


class TestCleanScrapedText:
    def test_collapses_multiple_spaces(self):
        assert clean_scraped_text("Producto    A     $100") == "Producto A $100"

    def test_trims_each_line(self):
        assert clean_scraped_text("   hola   \n   mundo   ") == "hola\nmundo"

    def test_collapses_consecutive_blank_lines(self):
        assert clean_scraped_text("a\n\n\n\nb") == "a\n\nb"

    def test_strips_leading_and_trailing_whitespace(self):
        assert clean_scraped_text("\n\n  contenido  \n\n") == "contenido"

    def test_deterministic(self):
        raw = "Precio:   $1.200\n\n\nStock: 5  "
        assert clean_scraped_text(raw) == clean_scraped_text(raw)

    def test_empty_input(self):
        assert clean_scraped_text("") == ""


class TestCleanScrapedTextNoise:
    @pytest.mark.parametrize(
        "noise_line",
        [
            "hace 3 minutos",
            "hace 5 días",
            "hace un momento",
            "hace 2 años",
            "updated 2 hours ago",
            "Posted 5 days ago",
            "just now",
            "ahora mismo",
        ],
    )
    def test_removes_relative_timestamps(self, noise_line):
        raw = f"Contenido relevante\n{noise_line}\nMás contenido"
        result = clean_scraped_text(raw)
        assert result == "Contenido relevante\nMás contenido"

    @pytest.mark.parametrize(
        "noise_line",
        [
            "1.234 visitas",
            "56 vistas",
            "120 me gusta",
            "shared 56 times",
            "compartido 12 veces",
            "comentarios: 45",
            "9 comentarios",
            "1,234 views",
        ],
    )
    def test_removes_dynamic_counters(self, noise_line):
        raw = f"Producto A: $1.200\n{noise_line}\nProducto B: $3.500"
        result = clean_scraped_text(raw)
        assert result == "Producto A: $1.200\nProducto B: $3.500"

    @pytest.mark.parametrize(
        "noise_line",
        [
            "Usamos cookies para mejorar tu experiencia",
            "Aceptar todas las cookies",
            "Política de cookies",
            "Gestionar cookies",
            "We use cookies to improve your experience",
            "Gestionar el consentimiento",
        ],
    )
    def test_removes_cookie_banners(self, noise_line):
        raw = f"Bienvenidos\n{noise_line}\nProducto A: $1.200"
        result = clean_scraped_text(raw)
        assert result == "Bienvenidos\nProducto A: $1.200"

    def test_keeps_relevant_content_with_numbers(self):
        # Líneas con números que NO son contadores no deben eliminarse.
        raw = (
            "Producto A: $1.200 | Producto B: $3.500\n"
            "Entrega: 48hs hábiles en AMBA\n"
            "Precios vigentes desde el 01/06/2026"
        )
        assert clean_scraped_text(raw) == raw

    def test_does_not_remove_me_gusta_in_sentence(self):
        # "me gusta" dentro de una oración (no como contador) se conserva.
        raw = "Me gusta este producto porque rinde mucho"
        assert clean_scraped_text(raw) == raw

    def test_noise_removal_is_deterministic(self):
        raw = "Oferta\nhace 3 minutos\n1.234 visitas\nProducto A: $100"
        assert clean_scraped_text(raw) == clean_scraped_text(raw)
        assert clean_scraped_text(raw) == "Oferta\nProducto A: $100"

    def test_mock_text_survives_cleaning(self):
        # El texto mock no debe perder líneas relevantes al limpiarse.
        from app.integrations.scraper import _MOCK_TEXT

        cleaned = clean_scraped_text(_MOCK_TEXT)
        assert "Distribuidora Ejemplo" in cleaned
        assert "Producto A: $1.200" in cleaned
        assert "ventas@ejemplo.com.ar" in cleaned
