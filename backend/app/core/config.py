from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Base de datos ────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://vigi:vigi@localhost:5432/vigi"

    # ─── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ─── Flags de desarrollo ──────────────────────────────────────────────────
    use_mocks: bool = True

    # ─── LLM ─────────────────────────────────────────────────────────────────
    llm_model: str = "gemini/gemini-2.0-flash"
    gemini_api_key: str = ""

    # ─── Langfuse ────────────────────────────────────────────────────────────
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # ─── Clerk ───────────────────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    clerk_webhook_secret: str = ""

    # ─── Cloudflare R2 ───────────────────────────────────────────────────────
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "vigi-snapshots"
    r2_endpoint: str = ""

    # ─── Apify ───────────────────────────────────────────────────────────────
    apify_token: str = ""

    # ─── MercadoLibre ────────────────────────────────────────────────────────
    ml_client_id: str = ""
    ml_client_secret: str = ""

    # ─── Resend ──────────────────────────────────────────────────────────────
    resend_api_key: str = ""

    # ─── Twilio ──────────────────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # ─── Mercado Pago ────────────────────────────────────────────────────────
    mp_access_token: str = ""
    mp_webhook_secret: str = ""

    # ─── URLs ────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"

    # ─── General ─────────────────────────────────────────────────────────────
    timezone: str = "America/Argentina/Buenos_Aires"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Singleton de acceso directo
settings = get_settings()
