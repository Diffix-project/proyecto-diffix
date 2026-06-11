# Diccionario de Datos

PostgreSQL + **pgvector**. Esquema gestionado con SQLAlchemy + Alembic
(`backend/app/domains/**/models.py`).

## Convenciones

- **PK:** `id` UUID (helper `uuid_pk()` en `app/core/base.py`).
- **Timestamps:** `TimestampMixin` aporta `created_at`/`updated_at` con timezone donde aplica;
  varias tablas declaran `created_at` propio con `server_default=now()`.
- **Tipos portables:** las columnas JSON usan `JSONB` en Postgres y `JSON` en SQLite (tests)
  vía `with_variant`. `Digest.insight_ids` usa `ARRAY(UUID)` en Postgres / `JSON` en SQLite.
- **Enumeraciones:** se modelan como `String` + `CheckConstraint` (portable a SQLite), no como
  tipos `ENUM` nativos.
- **Borrado:** FKs con `ON DELETE CASCADE` salvo donde se indique (`SET NULL` / `RESTRICT`).

## Relaciones

```
User 1─1 Company 1─N Competitor 1─N CompetitorSource
                                  │            │
                                  ├─N Snapshot ┤
                                  └─N Change ◄─┘ (before 0:1 / after 1:1 Snapshot)
                                        │
                                        1─1 Insight 1─N Notification
User 1─N Notification
User 1─N Digest
```

---

## `users`

Usuario de la app (autenticado vía Clerk). 1:1 con `companies`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `clerk_id` | String | **UNIQUE**, indexado. ID de Clerk |
| `email` | String | NOT NULL |
| `name` | String | NOT NULL |
| `plan` | String | NOT NULL, default `free`. Check: `free\|starter\|growth\|business` |
| `plan_expires_at` | DateTime(tz) | nullable (Mercado Pago gestiona vigencia) |
| `notif_email_instant` | Boolean | default `true` |
| `notif_email_digest` | Boolean | default `true` |
| `notif_whatsapp` | Boolean | default `false` |
| `whatsapp_number` | String | nullable |
| `created_at` / `updated_at` | DateTime(tz) | TimestampMixin |

Constraint: `ck_users_plan`.

## `companies`

Empresa del usuario (su contexto/rubro). 1:1 con `users`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `users.id` CASCADE, **UNIQUE** (1:1) |
| `name` | String | NOT NULL |
| `industry` | String | NOT NULL. Check: `food\|tech\|construction\|other` |
| `country` | String | NOT NULL, default `AR` |
| `created_at` | DateTime(tz) | server default now() |

Constraint: `ck_companies_industry`.

## `competitors`

Competidor monitoreado. N:1 con `companies`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `company_id` | UUID | FK → `companies.id` CASCADE, indexado |
| `name` | String | NOT NULL |
| `website_url` | String | NOT NULL |
| `is_active` | Boolean | default `true` |
| `created_at` / `updated_at` | DateTime(tz) | TimestampMixin |

## `competitor_sources`

Una fila por fuente activa de un competidor. N:1 con `competitors`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `competitor_id` | UUID | FK → `competitors.id` CASCADE, indexado |
| `source_type` | String | Check: `website\|mercadolibre\|jobs\|pdf` |
| `source_url` | String | nullable |
| `config` | JSONB/JSON | nullable (ej. `seller_id`, `since_days`) |
| `is_active` | Boolean | default `true` |
| `last_checked_at` | DateTime(tz) | nullable |
| `created_at` | DateTime(tz) | server default now() |

Constraint: `ck_competitor_sources_source_type`.

## `snapshots`

Estado histórico de una fuente en un momento dado.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `competitor_id` | UUID | FK → `competitors.id` CASCADE |
| `source_id` | UUID | FK → `competitor_sources.id` CASCADE |
| `source_type` | String | Check `source_type` |
| `content_hash` | String(64) | SHA256 hex |
| `content` | Text | contenido normalizado |
| `raw_url` | String | nullable |
| `captured_at` | DateTime(tz) | server default now() |

Índices: `ix_snapshots_competitor_source` (competitor_id, source_id), `ix_snapshots_captured_at`.

## `changes`

Cambio detectado entre dos snapshots de una fuente.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `competitor_id` | UUID | FK → `competitors.id` CASCADE |
| `source_id` | UUID | FK → `competitor_sources.id` CASCADE |
| `source_type` | String | Check `source_type` |
| `section` | String | Check: `pricing\|home\|features\|jobs\|pdf\|general` |
| `diff_text` | Text | unified diff legible |
| `diff_raw` | JSONB/JSON | nullable (`added`, `removed`) |
| `snapshot_before_id` | UUID | FK → `snapshots.id` **SET NULL**, nullable |
| `snapshot_after_id` | UUID | FK → `snapshots.id` **RESTRICT**, NOT NULL |
| `detected_at` | DateTime(tz) | server default now() |
| `status` | String | default `pending`. Check: `pending\|analyzing\|done\|failed\|ignored` |

Índices: `ix_changes_competitor_id`, `ix_changes_status`, `ix_changes_detected_at`.
Constraints: `ck_changes_source_type`, `ck_changes_section`, `ck_changes_status`.

## `insights`

Insight generado por el Analyst (LLM). 1:1 con `changes`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `change_id` | UUID | FK → `changes.id` CASCADE, **UNIQUE** (1:1) |
| `what_changed` | Text | NOT NULL |
| `why_it_matters` | Text | NOT NULL |
| `what_to_do` | Text | NOT NULL |
| `urgency` | String | Check: `alta\|media\|baja` |
| `llm_model` | String | modelo usado |
| `prompt_tokens` | Integer | NOT NULL |
| `completion_tokens` | Integer | NOT NULL |
| `langfuse_trace_id` | String | nullable |
| `generated_at` | DateTime(tz) | server default now() |
| `embedding` | Vector(1536) | nullable, **solo Postgres** (búsqueda semántica, post-MVP) |

Índices: `ix_insights_change_id`, `ix_insights_urgency`, `ix_insights_generated_at`.
Constraint: `ck_insights_urgency`.

## `notifications`

Registro de alertas enviadas. N:1 con `users` y `insights`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `users.id` CASCADE, indexado |
| `insight_id` | UUID | FK → `insights.id` CASCADE, indexado |
| `channel` | String | Check: `email_instant\|email_digest\|whatsapp` |
| `status` | String | default `pending`. Check: `pending\|sent\|failed` |
| `sent_at` | DateTime(tz) | nullable |
| `error_message` | Text | nullable |
| `created_at` | DateTime(tz) | server default now() |

Constraints: `ck_notifications_channel`, `ck_notifications_status`.

## `digests`

Resumen semanal enviado a un usuario. N:1 con `users`.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `users.id` CASCADE, indexado |
| `period_start` | DateTime(tz) | NOT NULL |
| `period_end` | DateTime(tz) | NOT NULL |
| `insight_ids` | ARRAY(UUID)/JSON | nullable (insights incluidos) |
| `status` | String | default `pending`. Check: `pending\|sent\|failed` |
| `sent_at` | DateTime(tz) | nullable |
| `created_at` | DateTime(tz) | server default now() |

Constraint: `ck_digests_status`.

---

## Enumeraciones (valores válidos)

| Concepto | Valores |
|----------|---------|
| Plan | `free`, `starter`, `growth`, `business` |
| Rubro empresa | `food`, `tech`, `construction`, `other` |
| Tipo de fuente | `website`, `mercadolibre`, `jobs`, `pdf` |
| Sección de cambio | `pricing`, `home`, `features`, `jobs`, `pdf`, `general` |
| Estado de cambio | `pending`, `analyzing`, `done`, `failed`, `ignored` |
| Urgencia de insight | `alta`, `media`, `baja` |
| Canal de notificación | `email_instant`, `email_digest`, `whatsapp` |
| Estado notif./digest | `pending`, `sent`, `failed` |
