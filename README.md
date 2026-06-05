# Diffix

SaaS de inteligencia competitiva automatizada para distribuidoras argentinas. Monitorea competidores, detecta cambios y genera insights accionables en español con IA.

## Levantar el entorno completo

```bash
cp .env.example .env
# Editar .env con las variables reales (dejar USE_MOCKS=true para desarrollo sin credenciales)

docker compose -f infra/docker-compose.yml up
```

Servicios disponibles:
- API: http://localhost:8000 — Swagger en http://localhost:8000/docs
- Frontend: http://localhost:5173
- Langfuse: http://localhost:3000

## Desarrollo local del backend (sin Docker)

Requiere Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```bash
cd backend

# Instalar dependencias
uv sync

# Copiar y configurar variables de entorno
cp ../.env.example ../.env

# Levantar la API
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# En otra terminal: levantar el worker
uv run celery -A app.core.celery_app.celery_app worker -l info

# En otra terminal: levantar el beat (scheduler)
uv run celery -A app.core.celery_app.celery_app beat -l info
```

## Migraciones de base de datos

```bash
cd backend

# Crear una nueva migración (después de modificar modelos)
uv run alembic revision --autogenerate -m "descripcion del cambio"

# Aplicar migraciones pendientes
uv run alembic upgrade head

# Ver estado actual
uv run alembic current
```

## Tests

```bash
cd backend
uv run pytest
```

## Lint y type-check

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```
