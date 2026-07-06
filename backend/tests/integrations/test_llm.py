"""
Tests para la integración con el LLM (LiteLLM + Langfuse).

Todos los tests mockean `litellm.completion` y el cliente Langfuse; no se
hacen llamadas reales a internet ni se requieren claves de Gemini/Langfuse.
"""

import json
from types import SimpleNamespace

import pytest

import app.integrations.llm as llm
from app.integrations.llm import (
    LLMError,
    LLMResponseError,
    LLMResult,
    complete_json,
)

VALID_INSIGHT = {
    "what_changed": "El competidor bajó precios.",
    "why_it_matters": "Afecta tu demanda.",
    "what_to_do": "Revisá tus márgenes.",
    "urgency": "alta",
}


def _fake_response(content: str, *, model="gemini-real", prompt_tokens=100, completion_tokens=50):
    """Construye un objeto con el shape que devuelve litellm.completion."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        model=model,
    )


@pytest.fixture
def real_mode(monkeypatch):
    """Activa el modo real y desactiva Langfuse (sin claves)."""
    monkeypatch.setattr("app.integrations.llm.settings.use_mocks", False)
    monkeypatch.setattr("app.integrations.llm.settings.llm_model", "google/gemini-test")
    monkeypatch.setattr("app.integrations.llm.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.integrations.llm.settings.langfuse_public_key", "")
    monkeypatch.setattr("app.integrations.llm.settings.langfuse_secret_key", "")
    # Reset del cache del cliente Langfuse entre tests.
    monkeypatch.setattr("app.integrations.llm._langfuse_client", None)
    monkeypatch.setattr("app.integrations.llm._langfuse_resolved", False)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Evita esperas reales del backoff entre reintentos."""
    monkeypatch.setattr("app.integrations.llm.time.sleep", lambda _s: None)


# ─── Modo mock ─────────────────────────────────────────────────────────────────


class TestMockMode:
    def test_mock_returns_example_insight(self, monkeypatch):
        monkeypatch.setattr("app.integrations.llm.settings.use_mocks", True)
        result = complete_json("cualquier prompt")

        assert isinstance(result, LLMResult)
        assert set(result.data) == {"what_changed", "why_it_matters", "what_to_do", "urgency"}
        assert result.data["urgency"] == "alta"
        assert result.prompt_tokens == 120
        assert result.completion_tokens == 80
        assert result.trace_id == "mock-trace-id"

    def test_mock_uses_override_model(self, monkeypatch):
        monkeypatch.setattr("app.integrations.llm.settings.use_mocks", True)
        result = complete_json("p", model="custom/model")
        assert result.model == "custom/model"

    def test_mock_no_network_call(self, monkeypatch):
        monkeypatch.setattr("app.integrations.llm.settings.use_mocks", True)

        def _boom(*a, **k):
            raise AssertionError("no debería llamar a litellm en modo mock")

        monkeypatch.setattr("app.integrations.llm.litellm.completion", _boom)
        complete_json("p")


# ─── Modo real: parsing ────────────────────────────────────────────────────────


class TestRealParsing:
    def test_parses_tokens_model_and_data(self, real_mode, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response(json.dumps(VALID_INSIGHT)),
        )
        result = complete_json("analizá este diff")

        assert result.data == VALID_INSIGHT
        assert result.model == "gemini-real"
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50
        # Sin Langfuse configurado, no hay trace_id.
        assert result.trace_id is None

    def test_sends_json_object_and_temperature(self, real_mode, monkeypatch):
        captured = {}

        def _capture(**kwargs):
            captured.update(kwargs)
            return _fake_response(json.dumps(VALID_INSIGHT))

        monkeypatch.setattr("app.integrations.llm.litellm.completion", _capture)
        complete_json("un prompt", temperature=0.7)

        assert captured["response_format"] == {"type": "json_object"}
        assert captured["temperature"] == 0.7
        assert captured["model"] == "google/gemini-test"
        assert captured["messages"] == [{"role": "user", "content": "un prompt"}]
        assert captured["api_key"] == "test-key"

    def test_invalid_json_raises_response_error(self, real_mode, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response("esto no es json {"),
        )
        with pytest.raises(LLMResponseError):
            complete_json("p")

    def test_non_json_content_type_raises_response_error(self, real_mode, monkeypatch):
        # content=None → json.loads lanza TypeError → LLMResponseError.
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response(None),
        )
        with pytest.raises(LLMResponseError):
            complete_json("p")

    def test_missing_usage_defaults_tokens_to_zero(self, real_mode, monkeypatch):
        resp = _fake_response(json.dumps(VALID_INSIGHT))
        resp.usage = None  # algunos providers no devuelven usage
        monkeypatch.setattr("app.integrations.llm.litellm.completion", lambda **k: resp)

        result = complete_json("p")

        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.data == VALID_INSIGHT


# ─── Modo real: reintentos ─────────────────────────────────────────────────────


class TestRetries:
    def test_retries_then_succeeds(self, real_mode, monkeypatch):
        calls = {"n": 0}

        def _flaky(**kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                raise llm.litellm.RateLimitError("rate limited", llm_provider="gemini", model="x")
            return _fake_response(json.dumps(VALID_INSIGHT))

        monkeypatch.setattr("app.integrations.llm.litellm.completion", _flaky)
        result = complete_json("p")

        assert calls["n"] == 3  # 1 inicial + 2 reintentos
        assert result.data == VALID_INSIGHT

    def test_persistent_transient_error_raises_llm_error(self, real_mode, monkeypatch):
        def _always_timeout(**kwargs):
            raise llm.litellm.Timeout("timeout", llm_provider="gemini", model="x")

        monkeypatch.setattr("app.integrations.llm.litellm.completion", _always_timeout)
        with pytest.raises(LLMError):
            complete_json("p")

    def test_non_retryable_api_error_not_retried(self, real_mode, monkeypatch):
        calls = {"n": 0}

        def _api_error(**kwargs):
            calls["n"] += 1
            raise llm.litellm.APIError(500, "boom", llm_provider="gemini", model="x")

        monkeypatch.setattr("app.integrations.llm.litellm.completion", _api_error)
        with pytest.raises(LLMError):
            complete_json("p")
        assert calls["n"] == 1  # no se reintenta


# ─── Modo real: tracing Langfuse ───────────────────────────────────────────────


class _FakeGeneration:
    def __init__(self):
        self.trace_id = "trace-abc-123"
        self.updates = []
        self.ended = False

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def end(self):
        self.ended = True


class _FakeLangfuse:
    def __init__(self):
        self.generation = _FakeGeneration()
        self.observations = []
        self.flushed = 0

    def start_observation(self, **kwargs):
        self.observations.append(kwargs)
        return self.generation

    def flush(self):
        self.flushed += 1


@pytest.fixture
def langfuse_enabled(real_mode, monkeypatch):
    """Modo real con un cliente Langfuse falso inyectado."""
    fake = _FakeLangfuse()
    monkeypatch.setattr("app.integrations.llm._langfuse_client", fake)
    monkeypatch.setattr("app.integrations.llm._langfuse_resolved", True)
    return fake


class TestTracing:
    def test_trace_id_propagated_and_generation_recorded(self, langfuse_enabled, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response(json.dumps(VALID_INSIGHT)),
        )
        monkeypatch.setattr("app.integrations.llm._estimate_cost", lambda r: 0.0021)

        result = complete_json("p")

        assert result.trace_id == "trace-abc-123"
        gen = langfuse_enabled.generation
        assert gen.ended is True
        assert langfuse_enabled.flushed == 1
        # La generación registró output, tokens y costo.
        final_update = gen.updates[-1]
        assert final_update["usage_details"] == {"input": 100, "output": 50}
        assert final_update["cost_details"] == {"total": 0.0021}
        assert final_update["output"] == json.dumps(VALID_INSIGHT)

    def test_error_marks_generation_and_reraises(self, langfuse_enabled, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response("no json {"),
        )
        with pytest.raises(LLMResponseError):
            complete_json("p")

        gen = langfuse_enabled.generation
        assert gen.ended is True
        assert gen.updates[-1]["level"] == "ERROR"
        assert langfuse_enabled.flushed == 1

    def test_cost_none_passed_as_none(self, langfuse_enabled, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response(json.dumps(VALID_INSIGHT)),
        )
        monkeypatch.setattr("app.integrations.llm._estimate_cost", lambda r: None)

        result = complete_json("p")

        assert result.trace_id == "trace-abc-123"
        assert langfuse_enabled.generation.updates[-1]["cost_details"] is None

    def test_flush_failure_does_not_break_call(self, langfuse_enabled, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response(json.dumps(VALID_INSIGHT)),
        )
        # Un hiccup de Langfuse en flush() no debe romper la llamada al LLM.
        langfuse_enabled.flush = lambda: (_ for _ in ()).throw(RuntimeError("langfuse down"))

        result = complete_json("p")

        assert result.data == VALID_INSIGHT
        assert result.trace_id is None  # el fallo de tracing degrada a trace_id None

    def test_business_error_not_masked_by_tracing_failure(self, langfuse_enabled, monkeypatch):
        monkeypatch.setattr(
            "app.integrations.llm.litellm.completion",
            lambda **k: _fake_response("no json {"),
        )
        # Aunque flush() falle en el path de error, se re-lanza la excepción de negocio.
        langfuse_enabled.flush = lambda: (_ for _ in ()).throw(RuntimeError("langfuse down"))

        with pytest.raises(LLMResponseError):
            complete_json("p")


class TestLangfuseResolution:
    def test_no_keys_disables_tracing(self, real_mode):
        # real_mode deja las claves vacías → cliente None.
        assert llm._get_langfuse() is None

    def test_keys_present_builds_client(self, real_mode, monkeypatch):
        monkeypatch.setattr("app.integrations.llm.settings.langfuse_public_key", "pk")
        monkeypatch.setattr("app.integrations.llm.settings.langfuse_secret_key", "sk")
        built = {}

        class _FakeClient:
            def __init__(self, **kwargs):
                built.update(kwargs)

        monkeypatch.setattr("langfuse.Langfuse", _FakeClient)
        client = llm._get_langfuse()

        assert isinstance(client, _FakeClient)
        assert built["public_key"] == "pk"
        assert built["secret_key"] == "sk"

    def test_constructor_failure_returns_none_without_caching(self, real_mode, monkeypatch):
        monkeypatch.setattr("app.integrations.llm.settings.langfuse_public_key", "pk")
        monkeypatch.setattr("app.integrations.llm.settings.langfuse_secret_key", "sk")

        def _boom(**kwargs):
            raise RuntimeError("DNS not ready")

        monkeypatch.setattr("langfuse.Langfuse", _boom)

        assert llm._get_langfuse() is None
        # No se cachea el fallo transitorio: se puede reintentar en la próxima llamada.
        assert llm._langfuse_resolved is False
