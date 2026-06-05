"""
Tests para endpoints de listado paginado: /changes y /insights.

Verifican que la respuesta tiene la estructura {items, page, limit, total}
esperada por el frontend.
"""

from fastapi.testclient import TestClient

CHANGES_URL = "/api/v1/changes"
INSIGHTS_URL = "/api/v1/insights"


class TestChangesListing:
    def test_changes_returns_paginated_structure(self, client: TestClient, test_user):
        """GET /changes devuelve {items, page, limit, total}."""
        r = client.get(CHANGES_URL)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "page" in body
        assert "limit" in body
        assert "total" in body

    def test_changes_empty_result(self, client: TestClient, test_user):
        """Sin changes, items=[], total=0."""
        r = client.get(CHANGES_URL)
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1

    def test_changes_pagination_params(self, client: TestClient, test_user):
        """Los parámetros page y limit se reflejan en la respuesta."""
        r = client.get(CHANGES_URL, params={"page": 2, "limit": 5})
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 2
        assert body["limit"] == 5


class TestInsightsListing:
    def test_insights_returns_paginated_structure(self, client: TestClient, test_user):
        """GET /insights devuelve {items, page, limit, total}."""
        r = client.get(INSIGHTS_URL)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "page" in body
        assert "limit" in body
        assert "total" in body

    def test_insights_empty_result(self, client: TestClient, test_user):
        """Sin insights, items=[], total=0."""
        r = client.get(INSIGHTS_URL)
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_insights_pagination_params(self, client: TestClient, test_user):
        """Los parámetros page y limit se reflejan en la respuesta."""
        r = client.get(INSIGHTS_URL, params={"page": 3, "limit": 10})
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 3
        assert body["limit"] == 10
