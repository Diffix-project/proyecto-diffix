"""
Integración con LLM via LiteLLM + Langfuse.

Interfaz pública:
  complete_json(prompt, *, model=None, temperature=0.3) -> LLMResult

LLMResult expone: .data (dict), .model (str), .prompt_tokens (int),
                  .completion_tokens (int), .trace_id (str | None).

En modo mock devuelve un insight de ejemplo válido sin llamada de red.
En modo real usa LiteLLM con response_format=json_object (temp configurable,
default 0.3) y registra cada llamada en Langfuse (prompt, output, tokens,
latencia, costo, modelo). Cambiar de provider se hace solo con LLM_MODEL.
"""

import json
import logging
import time
from dataclasses import dataclass, field

import litellm

from app.core.config import settings

logger = logging.getLogger(__name__)

# Reintentos ante errores transitorios del provider (timeout, rate limit, 5xx),
# además del intento inicial. Default 2 → hasta 3 intentos totales.
_MAX_LLM_RETRIES = 2
# Base del backoff exponencial entre reintentos (segundos): 1s, 2s, 4s, ...
_RETRY_BACKOFF_BASE_SECONDS = 1.0
# Excepciones de LiteLLM que justifican reintentar (fallos transitorios).
_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    litellm.Timeout,
    litellm.RateLimitError,
    litellm.APIConnectionError,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
)

_MOCK_INSIGHT: dict = {
    "what_changed": "El competidor actualizó su página de precios con nuevos valores.",
    "why_it_matters": "Un recorte de precios del 15% puede afectar la demanda de tus productos.",
    "what_to_do": "Revisá tu lista de precios esta semana y evaluá si ajustás márgenes en SKUs clave.",
    "urgency": "alta",
}


class LLMError(Exception):
    """Error genérico de la integración con el LLM."""

    pass


class LLMResponseError(LLMError):
    """El modelo devolvió una respuesta que no es JSON válido."""

    pass


@dataclass
class LLMResult:
    """Resultado de una llamada al LLM."""

    data: dict = field(default_factory=dict)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    trace_id: str | None = None


# ─── Langfuse (tracing) ───────────────────────────────────────────────────────

# Cliente Langfuse cacheado a nivel módulo. None = tracing deshabilitado
# (faltan claves). Se resuelve una sola vez por proceso.
_langfuse_client = None
_langfuse_resolved = False


def _get_langfuse():
    """
    Devuelve el cliente Langfuse, o None si el tracing está deshabilitado.

    Degrada a no-op (None) si faltan las claves de Langfuse, para que la
    llamada al LLM nunca se rompa por un problema de observabilidad.
    """
    global _langfuse_client, _langfuse_resolved
    if _langfuse_resolved:
        return _langfuse_client

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        # Sin claves: decisión permanente, no tiene sentido reintentar.
        logger.debug("llm: Langfuse sin claves, tracing deshabilitado")
        _langfuse_resolved = True
        _langfuse_client = None
        return None

    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as e:  # pragma: no cover - defensivo, no debe romper la llamada
        # Fallo transitorio de construcción (p. ej. DNS al arrancar el worker):
        # no lo cacheamos para permitir reintentar en la próxima llamada.
        logger.warning("llm: no se pudo inicializar Langfuse, se reintentará: %s", e)
        return None

    _langfuse_client = client
    _langfuse_resolved = True
    return _langfuse_client


def _start_generation(langfuse, prompt: str, model: str, temperature: float):
    """Inicia la generación en Langfuse; devuelve None si el tracing falla."""
    try:
        return langfuse.start_observation(
            name="analyst-complete-json",
            as_type="generation",
            input=prompt,
            model=model,
            model_parameters={"temperature": temperature},
        )
    except Exception as e:  # pragma: no cover - el tracing nunca debe romper la llamada
        logger.warning("llm: no se pudo iniciar el trace de Langfuse: %s", e)
        return None


def _finish_generation(langfuse, generation, **update_kwargs) -> str | None:
    """
    Cierra la generación de Langfuse y devuelve su trace_id.

    Nunca propaga errores de tracing: un fallo de observabilidad no debe romper
    (ni enmascarar) la llamada al LLM.
    """
    if generation is None:
        return None
    try:
        generation.update(**update_kwargs)
        generation.end()
        trace_id = generation.trace_id
        langfuse.flush()
        return trace_id
    except Exception as e:  # pragma: no cover - el tracing nunca debe romper la llamada
        logger.warning("llm: error al registrar el trace de Langfuse: %s", e)
        return None


def _estimate_cost(response) -> float | None:
    """Estima el costo en USD de la respuesta vía LiteLLM, o None si no se puede."""
    try:
        return litellm.completion_cost(completion_response=response)
    except Exception:  # pragma: no cover - el costo es best-effort
        return None


# ─── Llamada al LLM ────────────────────────────────────────────────────────────


def _call_litellm(prompt: str, model: str, temperature: float):
    """
    Llama a LiteLLM reintentando ante errores transitorios con backoff exponencial.

    Raises:
        LLMError: Si el provider falla de forma persistente tras agotar los reintentos.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_LLM_RETRIES + 1):
        try:
            return litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                response_format={"type": "json_object"},
                # LiteLLM lee la key del env var del provider (p. ej. GEMINI_API_KEY);
                # pydantic-settings no la exporta al entorno, así que la pasamos
                # explícitamente. `or None` deja que otros providers usen su env var.
                api_key=settings.gemini_api_key or None,
            )
        except _RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            if attempt < _MAX_LLM_RETRIES:
                backoff = _RETRY_BACKOFF_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "llm: error transitorio (%s), reintento %d/%d en %.1fs",
                    type(e).__name__,
                    attempt + 1,
                    _MAX_LLM_RETRIES,
                    backoff,
                )
                time.sleep(backoff)
                continue
        except litellm.APIError as e:
            # Error no transitorio del provider: no reintentar.
            raise LLMError(f"Error del provider LLM: {e}") from e

    raise LLMError(
        f"El provider LLM falló tras {_MAX_LLM_RETRIES + 1} intentos: {last_exc}"
    ) from last_exc


def _parse_response(response) -> tuple[dict, str, str, int, int]:
    """
    Extrae (data, raw, model, prompt_tokens, completion_tokens) de la respuesta.

    Raises:
        LLMResponseError: Si el contenido no es JSON válido.
    """
    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise LLMResponseError(f"El modelo no devolvió JSON válido: {e}") from e

    # `usage` puede faltar o venir None según provider/respuesta truncada.
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    return (data, raw, response.model, prompt_tokens, completion_tokens)


def complete_json(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
) -> LLMResult:
    """
    Llama al LLM y devuelve el JSON parseado como LLMResult.

    Mock: devuelve insight de ejemplo con tokens simulados (`USE_MOCKS=true`).
    Real: llama a LiteLLM con response_format=json_object, registra el trace en
    Langfuse (si hay claves) y devuelve el JSON con tokens y trace_id.

    Raises:
        LLMResponseError: Si el modelo no devuelve JSON válido.
        LLMError: Si el provider falla de forma persistente.
    """
    effective_model = model or settings.llm_model

    if settings.use_mocks:
        logger.debug("llm [mock] complete_json model=%s", effective_model)
        return LLMResult(
            data=_MOCK_INSIGHT.copy(),
            model=effective_model,
            prompt_tokens=120,
            completion_tokens=80,
            trace_id="mock-trace-id",
        )

    langfuse = _get_langfuse()
    generation = None
    if langfuse is not None:
        generation = _start_generation(langfuse, prompt, effective_model, temperature)

    try:
        response = _call_litellm(prompt, effective_model, temperature)
        data, raw, resp_model, prompt_tokens, completion_tokens = _parse_response(response)
    except Exception as e:
        _finish_generation(langfuse, generation, level="ERROR", status_message=str(e))
        raise

    cost = _estimate_cost(response)
    trace_id = _finish_generation(
        langfuse,
        generation,
        output=raw,
        model=resp_model,
        usage_details={"input": prompt_tokens, "output": completion_tokens},
        cost_details={"total": cost} if cost is not None else None,
    )

    logger.debug(
        "llm complete_json model=%s tokens=%d/%d trace=%s",
        resp_model,
        prompt_tokens,
        completion_tokens,
        trace_id,
    )
    return LLMResult(
        data=data,
        model=resp_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        trace_id=trace_id,
    )
