"""
Tests para la integración con la API de MercadoLibre.

Todos los tests mockean las llamadas HTTP usando respx.
"""

import pytest
import respx
from httpx import Response

from app.integrations.mercadolibre import (
    MercadoLibreAPIError,
    MercadoLibreAuthError,
    _headers,
    _token_cache,
    get_access_token,
    get_seller_listings,
    get_seller_reputation,
    get_seller_state,
)


@pytest.fixture(autouse=True)
def clear_token_cache():
    """Limpia el cache de tokens antes de cada test."""
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0.0
    yield
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0.0


@pytest.fixture
def ml_settings(monkeypatch):
    """Configura settings de MercadoLibre para tests."""
    monkeypatch.setattr("app.integrations.mercadolibre.settings.ml_client_id", "test_client_id")
    monkeypatch.setattr(
        "app.integrations.mercadolibre.settings.ml_client_secret", "test_client_secret"
    )
    monkeypatch.setattr(
        "app.integrations.mercadolibre.settings.ml_api_base_url",
        "https://api.mercadolibre.com",
    )


class TestGetAccessToken:
    """Tests para get_access_token()."""

    @respx.mock
    def test_get_access_token_success(self, ml_settings):
        """Test: get_access_token() retorna token válido."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "TEST_ACCESS_TOKEN",
                    "token_type": "bearer",
                    "expires_in": 21600,
                    "scope": "read write",
                },
            )
        )

        token = get_access_token()

        assert token == "TEST_ACCESS_TOKEN"
        assert _token_cache["access_token"] == "TEST_ACCESS_TOKEN"

    @respx.mock
    def test_token_is_cached(self, ml_settings):
        """Test: token se cachea (segunda llamada no hace POST)."""
        route = respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "CACHED_TOKEN",
                    "token_type": "bearer",
                    "expires_in": 21600,
                },
            )
        )

        token1 = get_access_token()
        token2 = get_access_token()

        assert token1 == "CACHED_TOKEN"
        assert token2 == "CACHED_TOKEN"
        assert route.call_count == 1

    @respx.mock
    def test_auth_error_401(self, ml_settings):
        """Test: error de auth 401 lanza excepción."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(401, json={"error": "invalid_client"})
        )

        with pytest.raises(MercadoLibreAuthError) as exc_info:
            get_access_token()

        assert "401" in str(exc_info.value)

    @respx.mock
    def test_auth_error_403(self, ml_settings):
        """Test: error de auth 403 lanza excepción."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(403, json={"error": "forbidden"})
        )

        with pytest.raises(MercadoLibreAuthError) as exc_info:
            get_access_token()

        assert "403" in str(exc_info.value)

    def test_missing_credentials(self, monkeypatch):
        """Test: credenciales faltantes lanzan excepción."""
        monkeypatch.setattr("app.integrations.mercadolibre.settings.ml_client_id", "")
        monkeypatch.setattr("app.integrations.mercadolibre.settings.ml_client_secret", "")

        with pytest.raises(MercadoLibreAuthError) as exc_info:
            get_access_token()

        assert "requeridos" in str(exc_info.value)


class TestHeaders:
    """Tests para _headers()."""

    @respx.mock
    def test_headers_contains_bearer_token(self, ml_settings):
        """Test: _headers() retorna Authorization Bearer token."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "MY_TOKEN",
                    "token_type": "bearer",
                    "expires_in": 21600,
                },
            )
        )

        headers = _headers()

        assert headers["Authorization"] == "Bearer MY_TOKEN"
        assert headers["Accept"] == "application/json"


class TestGetSellerListings:
    """Tests para get_seller_listings()."""

    @respx.mock
    def test_get_seller_listings_success(self, ml_settings):
        """Test: get_seller_listings() retorna lista de listings."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "id": "MLA123",
                            "title": "Producto A",
                            "price": 15000.0,
                            "permalink": "https://mercadolibre.com/mla123",
                            "thumbnail": "https://thumb.com/a.jpg",
                            "last_updated": "2026-06-10T10:00:00Z",
                        },
                        {
                            "id": "MLA124",
                            "title": "Producto B",
                            "price": 8500.0,
                            "permalink": "https://mercadolibre.com/mla124",
                            "thumbnail": "https://thumb.com/b.jpg",
                            "last_updated": "2026-06-09T10:00:00Z",
                        },
                    ]
                },
            )
        )

        listings = get_seller_listings("123456")

        assert len(listings) == 2
        assert listings[0]["id"] == "MLA123"
        assert listings[0]["title"] == "Producto A"
        assert listings[0]["price"] == 15000.0
        assert listings[1]["id"] == "MLA124"

    @respx.mock
    def test_listings_sorted_by_last_updated_desc(self, ml_settings):
        """Test: listings ordenados por last_updated DESC."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "id": "MLA1",
                            "title": "Old",
                            "price": 100.0,
                            "permalink": "",
                            "thumbnail": "",
                            "last_updated": "2026-01-01T00:00:00Z",
                        },
                        {
                            "id": "MLA2",
                            "title": "New",
                            "price": 200.0,
                            "permalink": "",
                            "thumbnail": "",
                            "last_updated": "2026-06-01T00:00:00Z",
                        },
                    ]
                },
            )
        )

        listings = get_seller_listings("123")

        assert listings[0]["id"] == "MLA2"
        assert listings[1]["id"] == "MLA1"

    @respx.mock
    def test_seller_not_found_404(self, ml_settings):
        """Test: 404 en seller lanza excepción clara."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(404, json={"error": "not_found"})
        )

        with pytest.raises(MercadoLibreAPIError) as exc_info:
            get_seller_listings("999999")

        assert "no encontrado" in str(exc_info.value).lower()

    @respx.mock
    def test_rate_limit_429_retries(self, ml_settings, monkeypatch):
        """Test: 429 hace retry automático."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )

        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(429, headers={"Retry-After": "0"})
            return Response(
                200,
                json={"results": [{"id": "MLA1", "title": "Test", "price": 100.0}]},
            )

        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(side_effect=side_effect)

        monkeypatch.setattr("app.integrations.mercadolibre.time.sleep", lambda x: None)

        listings = get_seller_listings("123")

        assert len(listings) == 1
        assert call_count == 2

    @respx.mock
    def test_max_listings_limit(self, ml_settings):
        """Test: limita a max_listings resultados."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )

        results = [
            {
                "id": f"MLA{i}",
                "title": f"Producto {i}",
                "price": 100.0 * i,
                "permalink": "",
                "thumbnail": "",
                "last_updated": "2026-06-10T00:00:00Z",
            }
            for i in range(60)
        ]

        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(200, json={"results": results})
        )

        listings = get_seller_listings("123", max_listings=10)

        assert len(listings) == 10


class TestGetSellerReputation:
    """Tests para get_seller_reputation()."""

    @respx.mock
    def test_get_seller_reputation_success(self, ml_settings):
        """Test: get_seller_reputation() retorna datos de reputación."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/users/123456").mock(
            return_value=Response(
                200,
                json={
                    "nickname": "SELLER_TEST",
                    "seller_reputation": {
                        "level_id": "5_green",
                        "metrics": {"transactions_total": 1500},
                    },
                    "status": {"site_status": "active"},
                },
            )
        )

        reputation = get_seller_reputation("123456")

        assert reputation["nickname"] == "SELLER_TEST"
        assert reputation["level_id"] == "5_green"
        assert reputation["transactions_total"] == 1500
        assert reputation["site_status"] == "active"

    @respx.mock
    def test_reputation_not_found_404(self, ml_settings):
        """Test: 404 en reputación lanza excepción."""
        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/users/999999").mock(
            return_value=Response(404, json={"error": "not_found"})
        )

        with pytest.raises(MercadoLibreAPIError) as exc_info:
            get_seller_reputation("999999")

        assert "no encontrado" in str(exc_info.value).lower()


class TestGetSellerState:
    """Tests para get_seller_state()."""

    def test_get_seller_state_mock_mode(self, monkeypatch):
        """Test: modo mock retorna datos de ejemplo."""
        monkeypatch.setattr("app.integrations.mercadolibre.settings.use_mocks", True)

        state = get_seller_state("mock_seller_123")

        assert state["seller_id"] == "mock_seller_123"
        assert "reputation" in state
        assert "active_listings" in state
        assert "top_products" in state

    @respx.mock
    def test_get_seller_state_real_mode(self, ml_settings, monkeypatch):
        """Test: modo real combina listings + reputation."""
        monkeypatch.setattr("app.integrations.mercadolibre.settings.use_mocks", False)

        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "id": "MLA1",
                            "title": "Producto A",
                            "price": 15000.0,
                            "permalink": "",
                            "thumbnail": "",
                            "last_updated": "2026-06-10T00:00:00Z",
                        },
                        {
                            "id": "MLA2",
                            "title": "Producto B",
                            "price": 8500.0,
                            "permalink": "",
                            "thumbnail": "",
                            "last_updated": "2026-06-09T00:00:00Z",
                        },
                    ]
                },
            )
        )
        respx.get("https://api.mercadolibre.com/users/123456").mock(
            return_value=Response(
                200,
                json={
                    "nickname": "TEST_SELLER",
                    "seller_reputation": {
                        "level_id": "4_yellow",
                        "metrics": {"transactions_total": 500},
                    },
                    "status": {"site_status": "active"},
                },
            )
        )

        state = get_seller_state("123456")

        assert state["seller_id"] == "123456"
        assert state["nickname"] == "TEST_SELLER"
        assert state["reputation"]["level_id"] == "4_yellow"
        assert state["active_listings"] == 2
        assert len(state["top_products"]) == 2
        assert state["total_transactions"] == 500
        assert len(state["listings"]) == 2

    @respx.mock
    def test_seller_state_partial_error_listings(self, ml_settings, monkeypatch):
        """Test: error en listings no bloquea reputation."""
        monkeypatch.setattr("app.integrations.mercadolibre.settings.use_mocks", False)

        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(404, json={"error": "not_found"})
        )
        respx.get("https://api.mercadolibre.com/users/123456").mock(
            return_value=Response(
                200,
                json={
                    "nickname": "TEST",
                    "seller_reputation": {"level_id": "3_orange", "metrics": {}},
                    "status": {"site_status": "active"},
                },
            )
        )

        state = get_seller_state("123456")

        assert state["seller_id"] == "123456"
        assert state["nickname"] == "TEST"
        assert "listings_error" in state
        assert state["active_listings"] == 0

    @respx.mock
    def test_seller_state_partial_error_reputation(self, ml_settings, monkeypatch):
        """Test: error en reputation no bloquea listings."""
        monkeypatch.setattr("app.integrations.mercadolibre.settings.use_mocks", False)

        respx.post("https://api.mercadolibre.com/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "TOKEN", "expires_in": 21600},
            )
        )
        respx.get("https://api.mercadolibre.com/sites/MLA/search").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "id": "MLA1",
                            "title": "Producto",
                            "price": 100.0,
                            "permalink": "",
                            "thumbnail": "",
                            "last_updated": "2026-06-10T00:00:00Z",
                        }
                    ]
                },
            )
        )
        respx.get("https://api.mercadolibre.com/users/123456").mock(
            return_value=Response(404, json={"error": "not_found"})
        )

        state = get_seller_state("123456")

        assert state["seller_id"] == "123456"
        assert state["active_listings"] == 1
        assert "reputation_error" in state
