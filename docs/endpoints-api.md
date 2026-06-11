# Documentación de Endpoints (FastAPI)

API REST de vigi.ai. Definición en `backend/app/main.py` y `app/domains/**/router.py`.

## Convenciones

- **Prefijo:** todos los routers de dominio se montan bajo **`/api/v1`** (excepto `/health`).
- **Auth:** la mayoría de los endpoints requieren un usuario autenticado vía la dependencia
  `get_current_db_user` (JWT de **Clerk** en `Authorization: Bearer <token>`). Los **webhooks**
  (`/auth/webhook`, `/billing/webhook`) son públicos y se verifican por firma.
- **Aislamiento por usuario:** los servicios filtran siempre por el usuario/empresa autenticada;
  un recurso de otro usuario responde `404`.
- **Paginación:** los listados grandes devuelven `PaginatedResponse[T]`:
  `{ items: T[], page, limit, total }`. Query params `page` (≥1, default 1) y `limit`
  (1–100, default 20).
- **Docs interactivas:** Swagger en `/docs`, ReDoc en `/redoc`.
- **Errores:** `HTTPException` con `detail`. Ej. límite de plan → `403 plan_limit_reached`.

---

## Infra

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check (`{"status": "ok"}`) | No |

## Auth — `/api/v1/auth`

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/auth/webhook` | Webhook de Clerk (upsert de usuario). Verifica firma | No (firma) |
| GET | `/auth/me` | Devuelve el usuario autenticado (`UserOut`) | Sí |

## Competitors — `/api/v1/competitors`

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| GET | `/competitors` | Lista los competidores del usuario | 200 |
| POST | `/competitors` | Crea un competidor. **Valida límite de plan** | 201 / 403 |
| GET | `/competitors/{competitor_id}` | Detalle de un competidor | 200 / 404 |
| PUT | `/competitors/{competitor_id}` | Actualiza un competidor | 200 / 404 |
| DELETE | `/competitors/{competitor_id}` | Elimina un competidor | 204 / 404 |
| GET | `/competitors/{competitor_id}/sources` | Lista las fuentes del competidor | 200 |
| POST | `/competitors/{competitor_id}/sources` | Agrega una fuente (`website\|mercadolibre\|jobs\|pdf`) | 201 |
| DELETE | `/competitors/{competitor_id}/sources/{source_id}` | Elimina una fuente | 204 |

## Changes — `/api/v1/changes`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/changes` | Lista paginada. Filtros: `competitor_id`, `source_type`, `urgency`, `from_date`, `to_date` |
| GET | `/changes/{change_id}` | Detalle de un cambio |
| PUT | `/changes/{change_id}/ignore` | Marca el cambio como `ignored` |

## Insights — `/api/v1/insights`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/insights` | Lista paginada. Filtros: `urgency`, `competitor_id`, `from_date` |
| GET | `/insights/{insight_id}` | Detalle de un insight (4 campos + metadata LLM) |

## Notifications & Digests — `/api/v1`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/notifications/settings` | Preferencias de notificación del usuario |
| PUT | `/notifications/settings` | Actualiza preferencias (email instant/digest, WhatsApp) |
| GET | `/digests` | Lista los digests semanales del usuario |
| GET | `/digests/{digest_id}` | Detalle de un digest |

## Billing — `/api/v1/billing`

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/billing/plans` | Lista los planes (free/starter/growth/business) y sus límites | No |
| GET | `/billing/current` | Plan actual del usuario | Sí |
| POST | `/billing/checkout` | Crea un checkout de Mercado Pago, devuelve `url` | Sí |
| POST | `/billing/webhook` | Webhook de Mercado Pago. Actualiza el plan si el pago se aprueba | No (firma) |

**Planes** (`app/core/plans.py`):

| Plan | Precio USD | Límite competidores | Alertas |
|------|-----------|---------------------|---------|
| Free | 0 | 2 | Solo digest semanal por email |
| Starter | 49 | 5 | Email instantáneo + WhatsApp |
| Growth | 149 | 10 | Email instantáneo + WhatsApp |
| Business | 399 | ilimitado | Email instantáneo + WhatsApp + acceso API |

## Uploads — `/api/v1/uploads`

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| POST | `/uploads/pdf` | Sube un PDF (`multipart`: `file` + `competitor_id`) a R2 y encola `parse_pdf`. Crea una `CompetitorSource` tipo `pdf` | 202 / 400 / 404 |

Respuesta 202: `{ key, status: "encolado", source_id, competitor_id }`.

---

## Webhooks

- **`POST /api/v1/auth/webhook`** — Clerk. Hace upsert del usuario en `users` a partir del evento.
- **`POST /api/v1/billing/webhook`** — Mercado Pago. Si el pago está `approved`, actualiza
  `users.plan` del usuario (matcheado por `clerk_id`).

Ambos se verifican por firma (`svix` para Clerk, `verify_mp_webhook` para Mercado Pago) y son
públicos (sin JWT).
