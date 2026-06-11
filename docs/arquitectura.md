# Arquitectura del Sistema

Diffix (vigi.ai) es un SaaS de inteligencia competitiva para distribuidoras argentinas.
Monitorea competidores automáticamente, detecta cambios y genera insights accionables en
español con IA. **Todo el producto es en español.**

## Visión general

```
                         ┌──────────────┐
                         │   Frontend   │  React + TS (solo consume la API)
                         └──────┬───────┘
                                │ HTTPS /api/v1
                         ┌──────▼───────┐
                         │  API FastAPI │  recibe requests, encola en Celery
                         └──────┬───────┘
                                │ enqueue
                    ┌───────────▼────────────┐
        Redis ◄─────┤   Celery (broker +     ├─────► PostgreSQL + pgvector
        (broker)    │   result backend)      │       (estado y datos)
                    └───────────┬────────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │   Workers Celery           │  scraping, análisis LLM,
                  │   (mismo codebase)         │  notificaciones
                  └─────────────┬──────────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │  Beat (scheduler)          │  dispara monitoreo 3am AR
                  └────────────────────────────┘
```

## Componentes

- **API (FastAPI):** recibe requests, valida, encola trabajo en Celery. **No ejecuta
  trabajo pesado.** Expone REST bajo `/api/v1`.
- **Workers (Celery):** ejecutan scraping, análisis LLM y notificaciones. Proceso separado,
  **mismo codebase** que la API.
- **Orquestador:** código **determinista, nunca un LLM**. Celery Beat dispara el monitoreo
  diario a las 3am hora Argentina.
- **Frontend:** solo consume la API. Sin lógica de negocio.

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI + Celery/Redis + PostgreSQL/pgvector + SQLAlchemy/Alembic |
| Gestor de paquetes | `uv` (lockfile `uv.lock`), Python ≥ 3.12 |
| LLM | LiteLLM → Gemini (variable `LLM_MODEL`, cambiar provider sin tocar código) |
| Scraping | **Playwright** (Chromium headless). MercadoLibre vía API oficial. Jobs vía Apify |
| Auth | Clerk (JWT) |
| Storage | Cloudflare R2 (URLs firmadas, acceso privado) |
| Observabilidad LLM | Langfuse desde el día 1 |
| Frontend | React + TypeScript + Vite + TanStack Query + Zustand + Tailwind + shadcn/ui + React Router v7 |
| Servicios | Resend (email) · Twilio (WhatsApp) · Mercado Pago (pagos) · Railway (deploy) |
| Dev | `docker compose up` levanta API, worker, beat, frontend, PostgreSQL, Redis y Langfuse |

> **Regla de scraping:** nunca scrapear MercadoLibre ni LinkedIn directo. ML usa su API
> oficial; los jobs se obtienen vía Apify.

## Agentes

### Scout (sin LLM)

Obtiene el estado de cada fuente de un competidor, lo normaliza a texto, calcula el hash
**SHA256** y lo compara con el snapshot anterior. Si el diff es significativo guarda un
`Change`. **Un error en una fuente no detiene las demás** (aislamiento por fuente).

El dispatch por tipo de fuente usa el patrón Strategy (`app/agents/scout/strategies.py`):

| `source_type` | Estrategia | Fuente de datos |
|---------------|-----------|-----------------|
| `website` | `WebsiteStrategy` | Playwright (scraping real) |
| `mercadolibre` | `MercadoLibreStrategy` | API oficial de MercadoLibre |
| `jobs` | `JobsStrategy` | Apify |
| `pdf` | `PdfStrategy` | (pendiente) |

Lógica central en `app/agents/scout/core.py`: `fetch_source_content`, `compute_hash`,
`get_last_snapshot`, `create_snapshot`, `compute_diff`, `detect_section`, `create_change`.

### Analyst (LLM, temp 0.3)

Recibe un `change_id`, construye el prompt con el diff + contexto del competidor y el rubro,
llama al LLM vía `integrations.llm.complete_json` y genera un JSON con **4 campos**:
`what_changed`, `why_it_matters`, `what_to_do`, `urgency` (`alta|media|baja`). Valida el JSON,
reintenta hasta 2 veces y **nunca muestra un insight sin validar**. Registra todo en Langfuse.

## Flujo de monitoreo diario (end-to-end)

1. **Beat** dispara `run_daily_monitoring` a las 3am AR.
2. Encola un `scout_competitor(competitor_id)` por cada competidor activo.
3. `scout_competitor` recorre las fuentes activas del competidor. Por cada una:
   - `fetch_source_content` → contenido (texto normalizado).
   - `compute_hash` (SHA256). Si coincide con el último snapshot → sin cambios, actualiza
     `last_checked_at` y sigue.
   - Si difiere → crea `Snapshot`, calcula `diff`, detecta `section`, crea `Change` (`pending`)
     y encola `analyze_change(change_id)`.
   - **Aislamiento:** un fallo en una fuente (`ScraperError`, `NotImplementedError`, etc.) se
     loguea, hace `rollback` y continúa con las demás.
4. **Analyst** (`analyze_change`) genera el `Insight`. Si `urgency == "alta"`, encola
   `notify_instant(insight_id)`.
5. **Notificaciones:** email instantáneo (Resend) + WhatsApp (Twilio) según preferencias y plan.
6. **Digest semanal** (`send_weekly_digests`, lunes 9am AR): resume los 3-5 insights más
   relevantes de la semana por usuario.

## Scraping con Playwright (DIX-18)

`integrations/scraper.py` expone `fetch_clean_text(url) -> str`:

- **Modo mock** (`USE_MOCKS=true`): devuelve texto fijo de ejemplo sin tocar la red ni instanciar
  Playwright (desarrollo local y CI).
- **Modo real:** usa la **API síncrona** de Playwright (`playwright.sync_api`), acorde al caller
  síncrono (worker Celery → strategy):
  - Lanza Chromium **headless**, navega con `wait_until="networkidle"` y timeout configurable
    (`SCRAPER_TIMEOUT_MS`, default 30000), extrae el `inner_text` del body.
  - **Browser por llamada**, cerrado en `finally` (sin leaks de Chromium).
  - **Limpieza determinista** (`clean_scraped_text`): elimina ruido dinámico (timestamps
    relativos, contadores, banners de cookies) con regex compilados y normaliza whitespace,
    para que el hash sea estable entre re-runs.
  - **Robustez:** reintentos con backoff exponencial (`SCRAPER_MAX_RETRIES`, default 2) ante
    timeouts/errores de red; detección anti-bot (HTTP 403/429 y CAPTCHA) → `ScraperError`
    controlado, sin reintentar y sin tumbar el worker.
  - User-agent realista de Chrome desktop + viewport para reducir detección de bots.

En producción el worker corre sobre la imagen oficial `mcr.microsoft.com/playwright/python`
(Chromium + dependencias del sistema preinstaladas); el paquete `playwright` está pinneado al
tag de la imagen para evitar drift browser↔pip.

## Orquestación (Celery Beat)

`app/core/celery_app.py` — zona horaria `America/Argentina/Buenos_Aires`, serialización JSON.

| Tarea | Schedule | Cola |
|-------|----------|------|
| `run_daily_monitoring` | todos los días 3:00 AR | `monitoring` |
| `send_weekly_digests` | lunes 9:00 AR | `notifications` |

Tareas registradas en `app/workers/tasks.py`: `run_daily_monitoring`, `scout_competitor`,
`analyze_change`, `notify_instant`, `send_weekly_digests`, `parse_pdf`.

## Integraciones

Todas siguen el mismo patrón: chequear `settings.use_mocks` temprano; en mock devuelven datos
de ejemplo, en real ejecutan la llamada (o lanzan `NotImplementedError` si su fase aún no se
implementó). Módulos en `app/integrations/`.

| Integración | Para qué | Estado real |
|-------------|----------|-------------|
| `scraper` | Scraping web (Playwright) | ✅ Implementado (DIX-18) |
| `mercadolibre` | Estado de vendedor (API oficial) | ✅ Implementado (DIX-19) |
| `apify` | Ofertas de trabajo | ⏳ Mock |
| `llm` | LLM vía LiteLLM + Langfuse | ⏳ Mock (fase Analyst) |
| `email` | Resend | ⏳ Mock (fase Notificaciones) |
| `whatsapp` | Twilio | ⏳ Mock (fase Notificaciones) |
| `payments` | Mercado Pago | Checkout + webhook |
| `storage` | Cloudflare R2 (URLs firmadas) | Por integrar |

## Reglas críticas

- **Langfuse en cada llamada LLM:** prompt, response, tokens, latencia, costo.
- **Todos los estados de procesos en DB** (`pending/analyzing/done/failed`) para debugging.
- **PDFs en R2** con URLs firmadas (acceso privado).
- **Límite de competidores por plan** — Free: 2, Starter: 5, Growth: 10, Business: ilimitado.
  Error 403 `plan_limit_reached` si se supera (lógica en `app/core/plans.py`).

## Fuera del MVP

No implementar: chat con agentes, Writer Agent, Discovery Agent, Slack, CRM, API pública,
app móvil, multi-idioma, SSO, microservicios, fine-tuning, Ollama en prod. Si surge → post-MVP.
