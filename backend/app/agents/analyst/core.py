"""Core del Analyst Agent.

Orquesta la generación de insights: construye el prompt, llama al LLM,
valida la respuesta y reintenta hasta 3 intentos en total.
"""

import logging
from dataclasses import dataclass

from app.agents.analyst.prompt import build_prompt
from app.agents.analyst.validation import InvalidInsightError, validate_insight
from app.integrations.llm import complete_json

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


class AnalystError(Exception):
    """El Analyst no pudo generar un insight válido tras todos los reintentos."""


@dataclass
class AnalystResult:
    """Resultado de una generación de insight exitosa."""

    data: dict
    model: str
    prompt_tokens: int
    completion_tokens: int
    trace_id: str | None


def generate_insight(
    diff_text: str,
    competitor_name: str,
    industry: str,
    section: str,
) -> AnalystResult:
    """
    Genera un insight validado a partir de un Change.

    Realiza hasta 3 intentos (1 inicial + 2 reintentos) ante fallos de
    validación o errores del LLM. Si tras los 3 intentos no se obtiene un
    insight válido, lanza `AnalystError`.

    Args:
        diff_text: Texto del diff detectado por el Scout.
        competitor_name: Nombre del competidor.
        industry: Rubro de la empresa del usuario.
        section: Sección donde ocurrió el cambio.

    Returns:
        AnalystResult con el insight validado y metadata del LLM.

    Raises:
        AnalystError: Si no se pudo generar un insight válido.
    """
    prompt = build_prompt(diff_text, competitor_name, industry, section)
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            llm_result = complete_json(prompt, temperature=0.3)
            validate_insight(llm_result.data)

            logger.info(
                "generate_insight: insight válido generado en intento %d/%d "
                "(model=%s, prompt_tokens=%d, completion_tokens=%d)",
                attempt,
                MAX_ATTEMPTS,
                llm_result.model,
                llm_result.prompt_tokens,
                llm_result.completion_tokens,
            )

            return AnalystResult(
                data=llm_result.data,
                model=llm_result.model,
                prompt_tokens=llm_result.prompt_tokens,
                completion_tokens=llm_result.completion_tokens,
                trace_id=llm_result.trace_id,
            )
        except InvalidInsightError as exc:
            last_error = exc
            logger.warning(
                "generate_insight: intento %d/%d falló por validación: %s",
                attempt,
                MAX_ATTEMPTS,
                exc.reason,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(
                "generate_insight: intento %d/%d falló por error del LLM: %s",
                attempt,
                MAX_ATTEMPTS,
                exc,
            )

    raise AnalystError(
        f"No se pudo generar un insight válido tras {MAX_ATTEMPTS} intentos"
    ) from last_error
