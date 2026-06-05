"""
Definición declarativa de planes y límites de vigi.ai.

No tiene dependencia de la DB — se puede importar desde cualquier capa.
Los dominios de billing y competitors lo usan para verificar límites.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    nombre: str
    precio_usd: int
    limite_competidores: int | None  # None = ilimitado
    descripcion_alertas: str


PLANES: dict[str, Plan] = {
    "free": Plan(
        nombre="Free",
        precio_usd=0,
        limite_competidores=2,
        descripcion_alertas="Solo digest semanal por email",
    ),
    "starter": Plan(
        nombre="Starter",
        precio_usd=49,
        limite_competidores=5,
        descripcion_alertas="Email instantáneo + WhatsApp",
    ),
    "growth": Plan(
        nombre="Growth",
        precio_usd=149,
        limite_competidores=10,
        descripcion_alertas="Email instantáneo + WhatsApp",
    ),
    "business": Plan(
        nombre="Business",
        precio_usd=399,
        limite_competidores=None,
        descripcion_alertas="Email instantáneo + WhatsApp + acceso API",
    ),
}

# Lista ordenada para mostrar en el frontend (billing/plans)
PLANES_ORDENADOS = ["free", "starter", "growth", "business"]


def competitor_limit(plan: str) -> int | None:
    """
    Devuelve el límite de competidores para el plan dado.
    Retorna None si el plan es ilimitado (business).
    Lanza KeyError si el plan no existe.
    """
    return PLANES[plan.lower()].limite_competidores


def is_within_limit(plan: str, current_count: int) -> bool:
    """
    Retorna True si el usuario puede agregar un competidor más.
    False si ya alcanzó el límite del plan.
    """
    limit = competitor_limit(plan)
    if limit is None:
        return True  # business: ilimitado
    return current_count < limit
