# Imagen base oficial de Playwright (Ubuntu jammy) con Chromium + deps del sistema
# preinstalados en /ms-playwright. El tag debe coincidir con el pin de `playwright`
# en pyproject.toml (1.60.*) para que el browser empaquetado matchee el paquete pip.
# uv gestiona su propio Python 3.12 (la imagen trae 3.10 de sistema, no se usa).
# El worker y beat usan la misma imagen con un command override en docker-compose.yml.

FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy AS base

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
