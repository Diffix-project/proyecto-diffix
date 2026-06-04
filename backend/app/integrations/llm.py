"""
Integración con LLM via LiteLLM + Langfuse.

Interfaz pública:
  complete_json(prompt, *, model=None, temperature=0.3) -> LLMResult

LLMResult expone: .data (dict), .model (str), .prompt_tokens (int),
                  .completion_tokens (int), .trace_id (str | None).

En modo mock devuelve un insight de ejemplo válido sin llamada de red.
En modo real usa LiteLLM con response_format=json_object y registra en Langfuse.
"""

import logging
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)

_MOCK_INSIGHT: dict = {
    "what_changed": "El competidor actualizó su página de precios con nuevos valores.",
    "why_it_matters": "Un recorte de precios del 15% puede afectar la demanda de tus productos.",
    "what_to_do": "Revisá tu lista de precios esta semana y evaluá si ajustás márgenes en SKUs clave.",
    "urgency": "alta",
}


@dataclass
class LLMResult:
    """Resultado de una llamada al LLM."""

    data: dict = field(default_factory=dict)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    trace_id: str | None = None


def complete_json(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
) -> LLMResult:
    """
    Llama al LLM y devuelve el JSON parseado como LLMResult.

    Mock: devuelve insight de ejemplo con tokens simulados.
    Real: llama a LiteLLM con response_format=json_object y registra trace en Langfuse.
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

    # Real: fase Analyst
    # TODO (fase Analyst): implementar llamada real con LiteLLM + Langfuse:
    #
    # from langfuse import Langfuse
    # from langfuse.decorators import observe
    # import litellm
    #
    # langfuse = Langfuse(
    #     public_key=settings.langfuse_public_key,
    #     secret_key=settings.langfuse_secret_key,
    #     host=settings.langfuse_host,
    # )
    #
    # trace = langfuse.trace(name="analyst-complete-json", input={"prompt": prompt})
    # generation = trace.generation(name="llm-call", model=effective_model, input=prompt)
    #
    # response = litellm.completion(
    #     model=effective_model,
    #     messages=[{"role": "user", "content": prompt}],
    #     temperature=temperature,
    #     response_format={"type": "json_object"},
    # )
    #
    # raw = response.choices[0].message.content
    # data = json.loads(raw)
    # usage = response.usage
    #
    # generation.end(output=raw, usage={"input": usage.prompt_tokens, "output": usage.completion_tokens})
    # trace.update(output=data)
    #
    # return LLMResult(
    #     data=data,
    #     model=response.model,
    #     prompt_tokens=usage.prompt_tokens,
    #     completion_tokens=usage.completion_tokens,
    #     trace_id=trace.id,
    # )

    raise NotImplementedError("llm real mode: completar en fase Analyst")
