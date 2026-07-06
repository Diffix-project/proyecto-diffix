"""Validación del JSON de insight generado por el LLM.

Expone:
  InvalidInsightError: excepción lanzada cuando el insight no cumple el schema.
  validate_insight(data): valida que el dict tenga los 4 campos requeridos.
"""

from app.domains.insights.models import URGENCY_VALUES

REQUIRED_FIELDS = ("what_changed", "why_it_matters", "what_to_do", "urgency")


class InvalidInsightError(Exception):
    """El JSON devuelto por el LLM no cumple con el schema de insight."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Insight inválido: {reason}")


def validate_insight(data: dict) -> None:
    """
    Valida que `data` tenga los 4 campos requeridos, que no estén vacíos
    (tras strip) y que `urgency` sea uno de los valores permitidos.

    Args:
        data: dict parseado del JSON devuelto por el LLM.

    Raises:
        InvalidInsightError: Si falta un campo, está vacío o la urgencia es inválida.
    """
    if not isinstance(data, dict):
        raise InvalidInsightError("el insight no es un objeto JSON")

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise InvalidInsightError(f"falta el campo '{field}'")

        value = data[field]
        if not isinstance(value, str):
            raise InvalidInsightError(f"el campo '{field}' no es un string")

        if not value.strip():
            raise InvalidInsightError(f"el campo '{field}' está vacío")

    urgency = data["urgency"].strip().lower()
    if urgency not in URGENCY_VALUES:
        raise InvalidInsightError(
            f"urgency '{data['urgency']}' no es válida; valores permitidos: {URGENCY_VALUES}"
        )
