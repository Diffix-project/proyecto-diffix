"""
Tests del modulo scout.core (DIX-15).

Cubre:
- fetch_source_content: dispatch por source_type
- compute_hash: SHA256 deterministico
- normalize_to_text: serializacion estable
- Casos de error: source_type invalido, datos faltantes
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.scout.core import compute_hash, fetch_source_content, normalize_to_text


class TestComputeHash:
    def test_sha256_hex_64_chars(self):
        result = compute_hash("test content")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        content = "contenido de prueba"
        assert compute_hash(content) == compute_hash(content)

    def test_different_content_different_hash(self):
        assert compute_hash("a") != compute_hash("b")

    def test_empty_string(self):
        result = compute_hash("")
        assert len(result) == 64


class TestNormalizeToText:
    def test_dict_sorted_keys(self):
        data = {"z": 1, "a": 2, "m": 3}
        result = normalize_to_text(data)
        assert '"a": 2' in result
        assert result.index('"a"') < result.index('"m"') < result.index('"z"')

    def test_list_deterministic(self):
        data = [{"b": 2, "a": 1}, {"d": 4, "c": 3}]
        result1 = normalize_to_text(data)
        result2 = normalize_to_text(data)
        assert result1 == result2

    def test_nested_structures(self):
        data = {
            "seller_id": "test",
            "products": [{"price": 100, "name": "A"}, {"price": 50, "name": "B"}],
        }
        result = normalize_to_text(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_unicode_ensure_ascii_false(self):
        data = {"nombre": "Distribuidora Ejemplo"}
        result = normalize_to_text(data)
        assert "Distribuidora Ejemplo" in result
        assert "\\u" not in result


class TestFetchSourceContentWebsite:
    @patch("app.agents.scout.core.fetch_clean_text")
    def test_calls_scraper_with_url(self, mock_scraper):
        mock_scraper.return_value = "texto de la pagina"
        source = MagicMock()
        source.source_type = "website"
        source.source_url = "https://ejemplo.com"
        source.id = "test-id"

        result = fetch_source_content(source)

        assert result == "texto de la pagina"
        mock_scraper.assert_called_once_with("https://ejemplo.com")

    def test_raises_if_no_url(self):
        source = MagicMock()
        source.source_type = "website"
        source.source_url = None
        source.id = "test-id"

        with pytest.raises(ValueError, match="sin source_url"):
            fetch_source_content(source)


class TestFetchSourceContentMercadolibre:
    @patch("app.agents.scout.core.get_seller_state")
    def test_calls_ml_api_with_seller_id_from_config(self, mock_ml):
        mock_ml.return_value = {"seller_id": "123", "reputation": "good"}
        source = MagicMock()
        source.source_type = "mercadolibre"
        source.source_url = None
        source.config = {"seller_id": "123"}
        source.id = "test-id"

        result = fetch_source_content(source)

        mock_ml.assert_called_once_with("123")
        parsed = json.loads(result)
        assert parsed["seller_id"] == "123"

    @patch("app.agents.scout.core.get_seller_state")
    def test_falls_back_to_source_url_if_no_config(self, mock_ml):
        mock_ml.return_value = {"seller_id": "456"}
        source = MagicMock()
        source.source_type = "mercadolibre"
        source.source_url = "456"
        source.config = None
        source.id = "test-id"

        result = fetch_source_content(source)

        mock_ml.assert_called_once_with("456")
        assert json.loads(result)["seller_id"] == "456"

    def test_raises_if_no_seller_id(self):
        source = MagicMock()
        source.source_type = "mercadolibre"
        source.source_url = None
        source.config = {}
        source.id = "test-id"

        with pytest.raises(ValueError, match="sin seller_id"):
            fetch_source_content(source)


class TestFetchSourceContentJobs:
    @patch("app.agents.scout.core.get_job_postings")
    def test_calls_apify_with_competitor_name(self, mock_apify):
        mock_apify.return_value = [{"title": "Dev", "company": "Comp"}]
        competitor = MagicMock()
        competitor.name = "Empresa Test"
        source = MagicMock()
        source.source_type = "jobs"
        source.config = {}
        source.competitor = competitor
        source.id = "test-id"

        result = fetch_source_content(source)

        mock_apify.assert_called_once_with("Empresa Test", since_days=30)
        parsed = json.loads(result)
        assert len(parsed) == 1

    @patch("app.agents.scout.core.get_job_postings")
    def test_respects_since_days_from_config(self, mock_apify):
        mock_apify.return_value = []
        competitor = MagicMock()
        competitor.name = "Empresa"
        source = MagicMock()
        source.source_type = "jobs"
        source.config = {"since_days": 7}
        source.competitor = competitor
        source.id = "test-id"

        fetch_source_content(source)

        mock_apify.assert_called_once_with("Empresa", since_days=7)

    def test_raises_if_no_competitor(self):
        source = MagicMock()
        source.source_type = "jobs"
        source.config = {}
        source.competitor = None
        source.id = "test-id"

        with pytest.raises(ValueError, match="sin competidor"):
            fetch_source_content(source)


class TestFetchSourceContentPdf:
    def test_raises_not_implemented(self):
        source = MagicMock()
        source.source_type = "pdf"
        source.id = "test-id"

        with pytest.raises(NotImplementedError, match="pdf"):
            fetch_source_content(source)


class TestFetchSourceContentInvalid:
    def test_raises_on_unknown_type(self):
        source = MagicMock()
        source.source_type = "unknown_type"
        source.id = "test-id"

        with pytest.raises(ValueError, match="source_type desconocido"):
            fetch_source_content(source)


class TestIntegrationHashConsistency:
    """Verifica que el contenido normalizado produce hashes consistentes."""

    @patch("app.agents.scout.core.get_seller_state")
    def test_same_data_same_hash(self, mock_ml):
        mock_ml.return_value = {"seller_id": "123", "reputation": "good"}
        source = MagicMock()
        source.source_type = "mercadolibre"
        source.source_url = None
        source.config = {"seller_id": "123"}
        source.id = "test-id"

        content1 = fetch_source_content(source)
        hash1 = compute_hash(content1)

        content2 = fetch_source_content(source)
        hash2 = compute_hash(content2)

        assert hash1 == hash2
