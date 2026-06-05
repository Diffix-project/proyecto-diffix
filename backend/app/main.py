from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging


def _register_models() -> None:
    """Importa todos los módulos de modelos para que el registry de SQLAlchemy
    quede completo antes de configurar los mappers (relaciones por string como
    User → Notification fallan si la clase destino no fue importada)."""
    import app.domains.auth.models  # noqa: F401, PLC0415
    import app.domains.changes.models  # noqa: F401, PLC0415
    import app.domains.competitors.models  # noqa: F401, PLC0415
    import app.domains.digests.models  # noqa: F401, PLC0415
    import app.domains.insights.models  # noqa: F401, PLC0415
    import app.domains.notifications.models  # noqa: F401, PLC0415
    import app.domains.sources.models  # noqa: F401, PLC0415


def create_app() -> FastAPI:
    setup_logging()
    _register_models()

    app = FastAPI(
        title="vigi.ai API",
        description="API de inteligencia competitiva para distribuidoras argentinas.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — permite requests del frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Health check mínimo
    health_router = APIRouter()

    @health_router.get("/health", tags=["infra"])
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(health_router)

    # routers de dominios
    from app.domains.auth.router import router as auth_router  # noqa: PLC0415
    from app.domains.billing.router import router as billing_router  # noqa: PLC0415
    from app.domains.changes.router import router as changes_router  # noqa: PLC0415
    from app.domains.competitors.router import router as competitors_router  # noqa: PLC0415
    from app.domains.insights.router import router as insights_router  # noqa: PLC0415
    from app.domains.notifications.router import router as notifications_router  # noqa: PLC0415
    from app.domains.uploads.router import router as uploads_router  # noqa: PLC0415

    for domain_router in [
        auth_router,
        competitors_router,
        changes_router,
        insights_router,
        uploads_router,
        notifications_router,
        billing_router,
    ]:
        app.include_router(domain_router, prefix="/api/v1")

    return app


app = create_app()
