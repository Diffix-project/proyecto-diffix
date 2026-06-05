# Imagen base con Python 3.12.
# Para fases de scraping con Playwright se puede cambiar la base a
# mcr.microsoft.com/playwright/python:v1.45.0-jammy sin cambiar el resto del archivo.
# El worker y beat usan la misma imagen con un command override en docker-compose.yml.

FROM python:3.12-slim AS base

# Instalar dependencias del sistema necesarias para psycopg (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copiar manifiestos de dependencias primero (cache layer)
COPY pyproject.toml ./

# Instalar dependencias sin instalar el paquete en sí
RUN uv sync --no-dev --no-install-project

# Copiar el código fuente y la configuración de migraciones
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

# Sincronizar incluyendo el paquete (editable install)
RUN uv sync --no-dev

# --- stage final de producción ---
FROM base AS production

EXPOSE 8000

# La API corre con uvicorn. Worker y beat usan la misma imagen con command override:
#   worker: uv run celery -A app.core.celery_app.celery_app worker -l info
#   beat:   uv run celery -A app.core.celery_app.celery_app beat -l info
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
