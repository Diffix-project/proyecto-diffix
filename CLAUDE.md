# vigi.ai

SaaS de inteligencia competitiva para distribuidoras argentinas. Monitorea competidores automáticamente, detecta cambios y genera insights accionables en español con IA. Todo el producto es en español.

## Stack

**Backend:** FastAPI + Celery/Redis + PostgreSQL/pgvector + SQLAlchemy/Alembic  
**LLM:** LiteLLM → Gemini 2.0 Flash (variable `LLM_MODEL`, cambiar provider sin tocar código)  
**Scraping:** Playwright. MercadoLibre via API oficial. Jobs via Apify. Nunca scrapear ML ni LinkedIn directo.  
**Auth:** Clerk. Storage: Cloudflare R2. Observabilidad LLM: Langfuse desde el día 1.  
**Frontend:** React + TypeScript + Vite + TanStack Query + Zustand + Tailwind + shadcn/ui + React Router v7  
**Servicios:** Resend (email) · Twilio (WhatsApp) · Mercado Pago · Railway (deploy)  
**Dev:** `docker compose up` levanta todo (API, worker, frontend, PostgreSQL, Redis, Langfuse)

## Arquitectura

- **API (FastAPI):** recibe requests, encola en Celery. No ejecuta trabajo pesado.
- **Workers (Celery):** scraping, análisis LLM, notificaciones. Proceso separado, mismo codebase.
- **Orquestador:** código determinista, nunca un LLM. Celery Beat dispara monitoreo 3am AR.
- **Frontend:** solo consume la API, sin lógica de negocio.

## Agentes

**Scout** (sin LLM): obtiene estado de cada fuente, compara hash SHA256 con snapshot anterior, guarda `Change` si el diff es significativo. Un error en una fuente no detiene las demás.

**Analyst** (LLM, temp 0.3): recibe `change_id`, genera JSON con 4 campos (`what_changed`, `why_it_matters`, `what_to_do`, `urgency: alta|media|baja`), valida, reintenta hasta 2 veces. Nunca muestra insight sin validar. Registra todo en Langfuse.

## Reglas críticas

- Langfuse en cada llamada LLM: prompt, response, tokens, latencia, costo.
- Todos los estados de procesos en DB (`pending/analyzing/done/failed`) para debugging.
- PDFs en R2 con URLs firmadas (acceso privado).
- Límite de competidores por plan — Free: 2, Starter: 5, Growth: 10, Business: ilimitado. Error 403 `plan_limit_reached` si supera.

## Fuera del MVP

No implementar: chat con agentes, Writer Agent, Discovery Agent, Slack, CRM, API pública, app móvil, multi-idioma, SSO, microservicios, fine-tuning, Ollama en prod. Si surge → post-MVP.
