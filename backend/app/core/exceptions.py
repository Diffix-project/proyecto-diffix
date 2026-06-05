from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class PlanLimitReached(Exception):
    """Se lanza cuando el usuario intenta agregar un competidor superando el límite de su plan."""

    def __init__(self, plan: str, limit: int) -> None:
        self.plan = plan
        self.limit = limit
        super().__init__(f"Límite del plan '{plan}' alcanzado ({limit} competidores)")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra los handlers de excepciones de dominio en la app FastAPI.
    Agregar nuevos handlers aquí a medida que se definan nuevas excepciones.
    """

    @app.exception_handler(PlanLimitReached)
    async def plan_limit_handler(request: Request, exc: PlanLimitReached) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "code": "plan_limit_reached",
                "detail": (
                    f"Alcanzaste el límite de {exc.limit} competidores del plan {exc.plan}. "
                    "Actualizá tu plan para agregar más."
                ),
            },
        )
