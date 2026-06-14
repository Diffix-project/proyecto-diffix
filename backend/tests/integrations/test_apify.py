"""
Tests para la integración con la API de Apify.

Todos los tests mockean las llamadas HTTP usando respx; no se hacen
llamadas reales a internet ni se requiere un token de Apify.
"""

import pytest
import respx
from httpx import Response

from app.integrations.apify import (
    _MOCK_JOB_POSTINGS,
    ApifyAuthError,
    ApifyRunError,
    ApifyTimeoutError,
    _apify_headers,
    filter_postings_by_date,
    get_dataset_items,
    get_job_postings,
    normalize_job_posting,
    poll_run_result,
    run_linkedin_scraper,
    verify_token,
)

BASE_URL = "https://api.apify.com/v2"
ACTOR_PATH = "apify~linkedin-jobs-scraper"
RUNS_URL = f"{BASE_URL}/acts/{ACTOR_PATH}/runs"
RUN_URL = f"{BASE_URL}/acts/runs/RUN123"
DATASET_URL = f"{BASE_URL}/acts/runs/RUN123/dataset/items"


@pytest.fixture
def apify_settings(monkeypatch):
    """Configura settings de Apify (token, actor, base url) y modo real."""
    monkeypatch.setattr("app.integrations.apify.settings.apify_token", "TEST_TOKEN")
    monkeypatch.setattr(
        "app.integrations.apify.settings.apify_actor_id", "apify/linkedin-jobs-scraper"
    )
    monkeypatch.setattr("app.integrations.apify.settings.apify_api_base_url", BASE_URL)
    monkeypatch.setattr("app.integrations.apify.settings.use_mocks", False)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Evita esperas reales en polling y reintentos de rate limit."""
    monkeypatch.setattr("app.integrations.apify.time.sleep", lambda _seconds: None)


class TestHeaders:
    """Tests para _apify_headers()."""

    def test_headers_contains_bearer_token(self, apify_settings):
        headers = _apify_headers()
        assert headers["Authorization"] == "Bearer TEST_TOKEN"
        assert headers["Accept"] == "application/json"

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.setattr("app.integrations.apify.settings.apify_token", "")
        with pytest.raises(ApifyAuthError) as exc_info:
            _apify_headers()
        assert "apify_token" in str(exc_info.value)


class TestVerifyToken:
    """Tests para verify_token()."""

    @respx.mock
    def test_verify_token_success(self, apify_settings):
        respx.get(f"{BASE_URL}/users/me").mock(
            return_value=Response(200, json={"data": {"username": "diffix"}})
        )
        data = verify_token()
        assert data["username"] == "diffix"

    @respx.mock
    def test_verify_token_invalid_401(self, apify_settings):
        respx.get(f"{BASE_URL}/users/me").mock(
            return_value=Response(401, json={"error": {"message": "invalid token"}})
        )
        with pytest.raises(ApifyAuthError) as exc_info:
            verify_token()
        assert "401" in str(exc_info.value)


class TestRunLinkedinScraper:
    """Tests para run_linkedin_scraper()."""

    @respx.mock
    def test_run_sends_post_and_returns_run_id(self, apify_settings):
        route = respx.post(RUNS_URL).mock(
            return_value=Response(201, json={"data": {"id": "RUN123", "status": "READY"}})
        )

        run_id = run_linkedin_scraper(["Empresa SA"])

        assert run_id == "RUN123"
        assert route.called
        sent = route.calls.last.request
        assert sent.headers["Authorization"] == "Bearer TEST_TOKEN"
        import json

        assert json.loads(sent.content)["searchQueries"] == ["Empresa SA"]

    @respx.mock
    def test_run_auth_error_403(self, apify_settings):
        respx.post(RUNS_URL).mock(return_value=Response(403, json={"error": "forbidden"}))
        with pytest.raises(ApifyAuthError):
            run_linkedin_scraper(["Empresa SA"])


class TestPollRunResult:
    """Tests para poll_run_result()."""

    @respx.mock
    def test_poll_waits_until_succeeded(self, apify_settings):
        statuses = ["RUNNING", "RUNNING", "SUCCEEDED"]

        def side_effect(request):
            status = statuses.pop(0)
            return Response(200, json={"data": {"id": "RUN123", "status": status}})

        respx.get(RUN_URL).mock(side_effect=side_effect)

        data = poll_run_result("RUN123", timeout=60)

        assert data["status"] == "SUCCEEDED"
        assert statuses == []

    @respx.mock
    def test_poll_timeout_raises(self, apify_settings):
        respx.get(RUN_URL).mock(
            return_value=Response(200, json={"data": {"id": "RUN123", "status": "RUNNING"}})
        )
        with pytest.raises(ApifyTimeoutError) as exc_info:
            poll_run_result("RUN123", timeout=0)
        assert "RUN123" in str(exc_info.value)

    @respx.mock
    def test_poll_failed_run_raises(self, apify_settings):
        respx.get(RUN_URL).mock(
            return_value=Response(200, json={"data": {"id": "RUN123", "status": "FAILED"}})
        )
        with pytest.raises(ApifyRunError) as exc_info:
            poll_run_result("RUN123", timeout=60)
        assert "FAILED" in str(exc_info.value)


class TestGetDatasetItems:
    """Tests para get_dataset_items()."""

    @respx.mock
    def test_get_dataset_items_returns_list(self, apify_settings):
        items = [{"title": "Dev"}, {"title": "PM"}]
        respx.get(DATASET_URL).mock(return_value=Response(200, json=items))

        result = get_dataset_items("RUN123")

        assert result == items


class TestFilterPostingsByDate:
    """Tests para filter_postings_by_date()."""

    def test_filters_by_date(self):
        from datetime import UTC, datetime, timedelta

        recent = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        old = (datetime.now(UTC) - timedelta(days=90)).isoformat()
        items = [
            {"title": "Reciente", "postedAt": recent},
            {"title": "Viejo", "postedAt": old},
        ]

        result = filter_postings_by_date(items, since_days=30)

        assert len(result) == 1
        assert result[0]["title"] == "Reciente"

    def test_relative_date_parsing(self):
        items = [{"title": "Relativo", "postedAt": "2 days ago"}]
        result = filter_postings_by_date(items, since_days=30)
        assert len(result) == 1

    def test_unparseable_date_discarded(self):
        items = [{"title": "Sin fecha"}, {"title": "Basura", "postedAt": "no-es-fecha"}]
        result = filter_postings_by_date(items, since_days=30)
        assert result == []


class TestNormalizeJobPosting:
    """Tests para normalize_job_posting()."""

    def test_maps_fields(self):
        item = {
            "title": "Backend Dev",
            "companyName": "Empresa SA",
            "location": "CABA",
            "description": "Python/FastAPI",
            "postedAt": "2026-06-01T00:00:00Z",
            "jobUrl": "https://linkedin.com/jobs/1",
            "seniorityLevel": "Mid-Senior level",
        }

        result = normalize_job_posting(item)

        assert result["title"] == "Backend Dev"
        assert result["company"] == "Empresa SA"
        assert result["location"] == "CABA"
        assert result["url"] == "https://linkedin.com/jobs/1"
        assert result["seniority_level"] == "Mid-Senior level"
        assert result["posted_at"] == "2026-06-01T00:00:00Z"

    def test_shape_matches_mock(self):
        """El shape normalizado coincide con el del mock existente."""
        item = {"title": "X", "companyName": "Y", "postedAt": "2026-06-01"}
        result = normalize_job_posting(item)
        assert set(result.keys()) == set(_MOCK_JOB_POSTINGS[0].keys())


class TestGetJobPostings:
    """Tests para get_job_postings()."""

    def test_mock_mode(self, monkeypatch):
        monkeypatch.setattr("app.integrations.apify.settings.use_mocks", True)
        result = get_job_postings("Empresa SA", since_days=30)
        assert len(result) == len(_MOCK_JOB_POSTINGS)
        assert all(p["company"] == "Empresa SA" for p in result)

    @respx.mock
    def test_full_flow_real_mode(self, apify_settings):
        from datetime import UTC, datetime, timedelta

        recent = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        respx.post(RUNS_URL).mock(
            return_value=Response(201, json={"data": {"id": "RUN123", "status": "READY"}})
        )
        respx.get(RUN_URL).mock(
            return_value=Response(200, json={"data": {"id": "RUN123", "status": "SUCCEEDED"}})
        )
        respx.get(DATASET_URL).mock(
            return_value=Response(
                200,
                json=[
                    {
                        "title": "Backend Dev",
                        "companyName": "Empresa SA",
                        "location": "CABA",
                        "description": "Python",
                        "postedAt": recent,
                        "jobUrl": "https://linkedin.com/jobs/1",
                        "seniorityLevel": "Mid",
                    }
                ],
            )
        )

        result = get_job_postings("Empresa SA", since_days=30)

        assert len(result) == 1
        assert result[0]["title"] == "Backend Dev"
        assert result[0]["company"] == "Empresa SA"
        assert set(result[0].keys()) == set(_MOCK_JOB_POSTINGS[0].keys())

    @respx.mock
    def test_rate_limit_429_retries(self, apify_settings):
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(429, headers={"Retry-After": "0"})
            return Response(201, json={"data": {"id": "RUN123", "status": "READY"}})

        respx.post(RUNS_URL).mock(side_effect=side_effect)

        run_id = run_linkedin_scraper(["Empresa SA"])

        assert run_id == "RUN123"
        assert call_count == 2
