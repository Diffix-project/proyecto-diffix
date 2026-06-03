# MVP — Especificación para Desarrollo

> Este documento define qué construir, cómo hacerlo y qué no incluir en el MVP.
> Está pensado para ser usado como contexto de desarrollo desde el inicio del proyecto.

---

## Qué es el producto

SaaS de inteligencia competitiva automatizada para distribuidoras argentinas. El sistema monitorea competidores en múltiples fuentes digitales, detecta cambios relevantes y genera insights accionables en español usando agentes de IA.

El usuario carga sus competidores, el sistema hace el resto de forma autónoma: monitorea, detecta cambios, los interpreta con IA y notifica al usuario con recomendaciones concretas.

---

## Stack tecnológico

### Backend
- **Framework API:** FastAPI (Python)
- **Workers y tareas asíncronas:** Celery con Redis como broker
- **ORM:** SQLAlchemy con Alembic para migraciones
- **Base de datos:** PostgreSQL con extensión pgvector (instalada desde el inicio aunque no se use hasta post-MVP)
- **Scraping web:** Playwright (ejecuta JavaScript, no usar BeautifulSoup solo)
- **Job postings:** Apify API (no scraping directo de LinkedIn)
- **LLM:** LiteLLM como capa de abstracción. Provider inicial: Gemini 2.0 Flash. La variable de entorno `LLM_MODEL` define el modelo — cambiar provider no debe requerir cambios de código
- **Observabilidad LLM:** Langfuse desde el primer día. Cada llamada al LLM debe registrar prompt, response, tokens usados, latencia y costo
- **Storage de archivos:** Cloudflare R2 (compatible con S3 API) para snapshots y PDFs subidos
- **Auth:** Clerk. No construir autenticación propia

### Frontend
- **Framework:** React con TypeScript
- **Bundler:** Vite (no Create React App)
- **Server state:** TanStack Query (React Query)
- **Client state:** Zustand
- **Estilos:** Tailwind CSS
- **Componentes:** shadcn/ui
- **Routing:** React Router v7

### Servicios externos
- **Email:** Resend
- **WhatsApp:** Twilio (WhatsApp Business API)
- **Pagos:** Mercado Pago
- **Deploy:** Railway para el MVP

### Entorno de desarrollo
El entorno completo debe levantarse con `docker compose up`. Servicios incluidos: API, worker de Celery, frontend, PostgreSQL, Redis y Langfuse (self-hosted para desarrollo).

---

## Arquitectura general

El sistema tiene cuatro piezas principales que deben estar claramente separadas:

**1. API REST (FastAPI):** recibe requests del frontend, gestiona datos, expone los endpoints documentados más abajo. No ejecuta tareas pesadas directamente — las encola en Celery.

**2. Workers (Celery + Redis):** ejecutan todo el trabajo asíncrono: scraping, análisis con LLM, envío de notificaciones. Corren en un proceso separado pero comparten el mismo codebase que la API.

**3. Orquestador:** lógica de código determinista (no un LLM) que decide qué agente corre y cuándo. Celery Beat dispara el monitoreo diario a las 3am hora Argentina. El orquestador consulta todos los competidores activos y encola una tarea de Scout por cada uno.

**4. Frontend (React):** dashboard del usuario. Consume la API REST. No tiene lógica de negocio propia.

### Flujo de datos

El ciclo completo funciona así:

1. Celery Beat dispara el monitoreo diario
2. El orquestador encola una tarea de Scout por cada competidor activo
3. El Scout Agent corre para ese competidor: obtiene el estado actual de cada fuente configurada, compara con el snapshot anterior, y si detecta un cambio significativo lo guarda en la base de datos y encola una tarea de análisis
4. El Analyst Agent recibe el cambio, construye un prompt con el contexto del competidor y el rubro del usuario, llama al LLM via LiteLLM, valida que el JSON de respuesta tenga todos los campos requeridos, y guarda el insight en la base de datos
5. Si el insight tiene urgencia "alta", se encola una tarea de notificación instantánea (email + WhatsApp)
6. Los lunes a las 9am Argentina, Celery Beat dispara el digest semanal para todos los usuarios activos

---

## Los dos agentes del MVP

### Scout Agent

**Responsabilidad única:** detectar que algo cambió en las fuentes de un competidor. No usa LLM. Debe ser determinista y confiable.

**Fuentes que monitorea:**
- Sitio web del competidor: páginas home, pricing y features. Usar Playwright para ejecutar JavaScript. Extraer texto limpio del contenido visible. Filtrar ruido antes de comparar (fechas, horarios, contadores de visitas, años de copyright)
- MercadoLibre Argentina: usar la API oficial. Obtener reputación del vendedor, cantidad de publicaciones activas y precios de los productos más relevantes. Nunca scrapear MercadoLibre directamente
- Job postings: usar Apify. Buscar publicaciones de empleo del competidor en los últimos 30 días. Nunca scrapear LinkedIn directamente

**Cómo detecta cambios:**
- Guarda un snapshot del contenido actual de cada fuente (texto procesado + hash SHA256)
- Compara el hash con el snapshot anterior. Si son iguales, no hay cambio y termina
- Si son distintos, calcula el diff entre el contenido anterior y el actual
- El diff debe identificar qué sección cambió (pricing, features, jobs, general) y construir una descripción legible del cambio
- Solo se crea un Change en la DB si el diff es significativo (no mero ruido)
- Un error en una fuente no debe detener el monitoreo del resto de fuentes del mismo competidor. Loguear el error y continuar

**Output:** un objeto Change guardado en la DB con: competitor_id, source_type, sección afectada, descripción del diff, snapshot anterior y nuevo, y status "pending"

### Analyst Agent

**Responsabilidad única:** interpretar un Change y generar un Insight estructurado con LLM.

**Cómo funciona:**
- Recibe un change_id, lee el Change de la DB
- Construye un prompt que incluye: el diff detectado, el nombre del competidor, el rubro de la empresa del usuario (alimentos / tecnología / construcción / otro) como contexto
- Llama al LLM via LiteLLM con `response_format: json_object` y temperatura baja (0.3) para consistencia
- Valida que el JSON de respuesta tenga exactamente los cuatro campos requeridos con contenido no vacío y urgencia válida
- Si la validación falla, reintenta hasta 2 veces antes de marcar el Change como "failed"
- Nunca muestra al usuario un insight que no pasó la validación
- Registra el trace completo en Langfuse: prompt enviado, respuesta recibida, tokens usados, latencia, modelo
- Guarda el Insight en la DB con el ID del trace de Langfuse para trazabilidad

**Estructura del insight (JSON que produce el LLM):**
- `what_changed`: descripción clara y concisa de qué cambió, en una oración
- `why_it_matters`: por qué este cambio es relevante estratégicamente, en 1-2 oraciones
- `what_to_do`: acción concreta y específica que debería tomar el usuario esta semana, en 1-2 oraciones
- `urgency`: "alta" (cambio de precio, nuevo producto, expansión) / "media" (nuevo messaging, contrataciones) / "baja" (diseño, contenido menor)

---

## Base de datos — Tablas y relaciones

### Relaciones
```
users → companies (1:1)
companies → competitors (1:N)
competitors → competitor_sources (1:N)
competitors → snapshots (1:N)
competitors → changes (1:N)
changes → insights (1:1)
insights → notifications (1:N)
users → digests (1:N)
```

### Tabla: users
Campos: id (UUID PK), clerk_id (único, viene de Clerk), email, name, plan (free/starter/growth/business), plan_expires_at, created_at, updated_at

### Tabla: companies
Empresa del usuario. Campos: id, user_id (FK), name, industry (food/tech/construction/other), country (default AR), created_at

### Tabla: competitors
Campos: id, company_id (FK), name, website_url, is_active (boolean, default true), created_at, updated_at

### Tabla: competitor_sources
Una fila por cada fuente activa de un competidor. Campos: id, competitor_id (FK), source_type (website/mercadolibre/jobs/pdf), source_url, config (JSONB para parámetros específicos como seller_id de ML o company_name para Apify), is_active, last_checked_at, created_at

### Tabla: snapshots
Estado histórico de cada fuente. Campos: id, competitor_id (FK), source_id (FK), source_type, content_hash (SHA256), content (texto procesado), raw_url (URL al archivo en R2), captured_at. Índices en (competitor_id, source_id) y en captured_at

### Tabla: changes
Cambios detectados entre snapshots. Campos: id, competitor_id (FK), source_id (FK), source_type, section (pricing/home/features/jobs/pdf/general), diff_text (descripción legible), diff_raw (JSONB con líneas añadidas y removidas), snapshot_before (FK snapshots), snapshot_after (FK snapshots), detected_at, status (pending/analyzing/done/failed/ignored). Índices en competitor_id, status y detected_at

### Tabla: insights
Un insight por Change. Campos: id, change_id (FK único), what_changed, why_it_matters, what_to_do, urgency (alta/media/baja), llm_model, prompt_tokens, completion_tokens, langfuse_trace_id, generated_at, embedding (vector 1536 para post-MVP, puede ser null). Índices en change_id, urgency y generated_at

### Tabla: notifications
Registro de alertas enviadas. Campos: id, user_id (FK), insight_id (FK), channel (email_instant/email_digest/whatsapp), status (pending/sent/failed), sent_at, error_message, created_at

### Tabla: digests
Resúmenes semanales. Campos: id, user_id (FK), period_start, period_end, insight_ids (array de UUIDs), status (pending/sent/failed), sent_at, created_at

---

## API REST

Base URL: `/api/v1`  
Todos los endpoints requieren header `Authorization: Bearer <clerk_token>` excepto el webhook de Clerk.  
Respuestas en JSON. Paginación con parámetros `page` y `limit`.

### Auth
- `POST /auth/webhook` — Público. Webhook de Clerk. Crea el usuario en la DB cuando se registra en Clerk. Verificar firma del webhook con el secret de Clerk antes de procesar
- `GET /auth/me` — Retorna usuario autenticado, su empresa y plan actual

### Competitors
- `GET /competitors` — Lista todos los competidores del usuario autenticado
- `POST /competitors` — Crea competidor. Body: name, website_url, y array de sources a activar (source_type + config opcional)
- `GET /competitors/:id` — Detalle de un competidor
- `PUT /competitors/:id` — Actualiza name o website_url
- `DELETE /competitors/:id` — Soft delete: pone is_active en false, no borra de la DB
- `GET /competitors/:id/sources` — Lista fuentes configuradas del competidor
- `POST /competitors/:id/sources` — Agrega una fuente. Body: source_type, source_url opcional, config JSONB opcional
- `DELETE /competitors/:id/sources/:source_id` — Desactiva la fuente (is_active = false)

Regla de negocio en POST /competitors: verificar que el usuario no supere el límite de su plan (free: 2, starter: 5, growth: 10, business: ilimitado). Si supera, retornar 403 con código "plan_limit_reached"

### Changes e Insights
- `GET /changes` — Lista cambios del usuario paginados. Query params: competitor_id, source_type, urgency, from_date, to_date, page, limit
- `GET /changes/:id` — Detalle de un cambio con su insight asociado
- `PUT /changes/:id/ignore` — Marca el cambio como "ignored" para que no aparezca en el dashboard
- `GET /insights` — Lista insights del usuario paginados. Query params: urgency, competitor_id, from_date, page, limit
- `GET /insights/:id` — Detalle completo de un insight

### Upload PDF
- `POST /uploads/pdf` — Multipart form. Campos: file (PDF), competitor_id. El endpoint sube el archivo a R2, encola una tarea worker que extrae el texto con el LLM, y crea un snapshot + change si hay diferencias con el PDF anterior del mismo competidor

### Notificaciones
- `GET /notifications/settings` — Preferencias de notificación del usuario (qué canales activos, número de WhatsApp si configuró)
- `PUT /notifications/settings` — Actualiza preferencias. Body: email_instant (bool), email_digest (bool), whatsapp (bool), whatsapp_number
- `GET /digests` — Historial de digests enviados al usuario
- `GET /digests/:id` — Contenido de un digest específico

### Billing
- `GET /billing/plans` — Lista los planes disponibles con precios y límites
- `GET /billing/current` — Plan actual del usuario y fecha de vencimiento
- `POST /billing/checkout` — Crea sesión de pago en Mercado Pago. Body: plan_id. Retorna URL de redirección
- `POST /billing/webhook` — Público con verificación de firma. Webhook de Mercado Pago. Actualiza el plan del usuario en DB cuando el pago se confirma

---

## Sistema de notificaciones

### Email instantáneo
Se dispara cuando un insight tiene urgencia "alta". Debe llegar al usuario en menos de 2 minutos desde que se detectó el cambio. Usar Resend. El email debe incluir: nombre del competidor, qué cambió, por qué importa y qué hacer, con un link al dashboard.

### Digest semanal
Se envía los lunes a las 9am hora Argentina vía Celery Beat. Incluye los 3 a 5 insights más relevantes de la semana para ese usuario, agrupados por competidor y ordenados por urgencia. Si el usuario no tuvo ningún insight esa semana, no enviar el digest.

### WhatsApp
Solo para alertas de urgencia "alta", si el usuario configuró su número. Usar Twilio WhatsApp Business API. El mensaje debe ser conciso: competidor, qué cambió, qué hacer y link al dashboard. Formato compatible con WhatsApp (sin HTML).

---

## Frontend — Páginas requeridas

### Rutas
- `/` — Si el usuario está autenticado redirige a /dashboard. Si no, muestra la landing page
- `/login` — Componente de Clerk SignIn
- `/register` — Componente de Clerk SignUp
- `/dashboard` — Vista principal: timeline de insights con filtros por competidor, fuente, urgencia y fecha
- `/competitors` — Lista de competidores configurados con estado de cada uno
- `/competitors/new` — Formulario para agregar un nuevo competidor y sus fuentes
- `/competitors/:id` — Detalle del competidor, configuración de fuentes activas, historial de cambios
- `/settings` — Preferencias de notificaciones y datos del perfil
- `/settings/billing` — Plan actual, límites de uso y botón de upgrade

### Comportamiento del dashboard
- Los insights se muestran en orden cronológico inverso (más reciente primero)
- Cada insight muestra: nombre del competidor, fuente (web/ML/jobs/pdf), badge de urgencia con color (roja/amarilla/gris), tiempo transcurrido desde la detección, y los tres campos de texto (qué cambió, por qué importa, qué hacer)
- El campo "qué hacer" debe destacarse visualmente (fondo diferente) porque es el de mayor valor para el usuario
- Los filtros del sidebar son: urgencia (todas/alta/media/baja), fuente, competidor, y rango de fechas
- Cuando no hay insights todavía, mostrar un estado vacío que explica que el sistema está monitoreando y cuándo se espera el primer resultado
- Cuando el usuario en plan free intenta agregar un tercer competidor, mostrar un modal de upgrade antes de dejar avanzar con el formulario

---

## Planes y límites

| Plan | Precio | Competidores | Alertas disponibles |
|---|---|---|---|
| Free | $0 | 2 | Solo digest semanal por email |
| Starter | $49/mes | 5 | Email instantáneo + WhatsApp |
| Growth | $149/mes | 10 | Todo lo anterior |
| Business | $399/mes | Ilimitados | Todo lo anterior + acceso API |

El límite de competidores se verifica en el endpoint POST /competitors. Si el usuario llega al límite, el sistema no crea el competidor y retorna error 403 con código "plan_limit_reached". El frontend intercepta este error y muestra el modal de upgrade.

---

## Criterios de done por etapa

### Infraestructura base (semanas 5-7)
- `docker compose up` levanta todos los servicios sin errores
- Un usuario puede registrarse, y el webhook de Clerk crea automáticamente su registro en la DB
- Las migraciones de Alembic corren correctamente y crean todas las tablas
- Langfuse recibe traces de prueba
- La API tiene documentación Swagger accesible en /docs
- Deploy en Railway corriendo para API + worker

### Scout Agent (semanas 8-10)
- El scraper extrae texto limpio de sitios web con JavaScript
- El sistema detecta y registra un cambio cuando el contenido de una fuente cambia
- Los snapshots se almacenan en R2 con URL accesible
- La API de MercadoLibre retorna datos correctos dado un seller_id
- Apify retorna job postings para una empresa de prueba
- Celery Beat ejecuta el monitoreo según el schedule
- Un error en una fuente no detiene el monitoreo de otras fuentes del mismo competidor

### Analyst Agent (semanas 11-13)
- El agente genera un insight válido para cualquier Change en la DB
- El JSON del insight siempre tiene los 4 campos requeridos con contenido de calidad
- Si el LLM falla o devuelve JSON inválido, el agente reintenta y solo marca como "failed" tras 3 intentos
- Cada llamada al LLM aparece en Langfuse con toda la información de trazabilidad
- Al menos 25 de 30 casos de prueba manuales producen insights de calidad aceptable
- El tiempo de generación es menor a 30 segundos en el percentil 95

### Producto beta (semanas 14-16)
- El dashboard muestra insights con filtros funcionando correctamente
- El email de digest semanal llega correctamente a una cuenta de prueba
- El email de alerta instantánea llega en menos de 2 minutos tras detectarse un cambio de urgencia alta
- El upload y parsing de PDF genera un Change si hay diferencias con el PDF anterior
- Un usuario externo completa el onboarding (registro → competidor → primer insight) en menos de 5 minutos sin ayuda del equipo
- El paywall funciona correctamente cuando un usuario free intenta superar el límite de 2 competidores
- 5 usuarios externos usan el producto de forma autónoma

---

## Lo que NO está en el MVP

Cualquier feature de esta lista está fuera del scope. Si durante el desarrollo surge la tentación de agregar algo de esta lista, la respuesta es: post-MVP.

**Agentes:**
- Chat interface con los agentes (Advisor Agent) — requiere historial acumulado y RAG, va en Fase 4
- Predictor de roadmap del competidor — requiere 8+ semanas de datos históricos
- Writer Agent (battlecards, borradores de email, sugerencias de contenido) — va en Fase 3
- Discovery Agent automático de fuentes — el usuario configura fuentes manualmente en el MVP

**Integraciones:**
- Slack — baja prioridad para el segmento de distribuidoras
- CRM (HubSpot, Pipedrive) — agente de clientes perdidos va en Fase 5
- API pública para terceros — Fase 5

**Fuentes de datos:**
- Monitoreo directo de LinkedIn — solo job postings via Apify
- Noticias y prensa via SerpAPI — post-MVP
- Redes sociales más allá de lo básico

**Producto:**
- App móvil — solo web
- Exportación de reportes en PDF
- Multi-idioma — solo español
- SSO / SAML para enterprise
- Dashboard de analytics del propio uso del producto

**Infraestructura:**
- Microservicios — monolito + worker separado hasta tener tracción
- Fine-tuning de modelos propios
- Infraestructura propia de LLMs (Ollama en producción)

---

## Consideraciones importantes de implementación

**Sobre el scraping:** siempre respetar el robots.txt de los sitios. No scrapear contenido detrás de login. Implementar rate limiting para no sobrecargar los servidores objetivo. Un competidor se monitorea cada 24 horas, no más frecuente. Los errores de scraping deben loguearse pero nunca propagarse al usuario.

**Sobre los costos de LLM:** monitorear el gasto de tokens desde el primer día con Langfuse. No todas las tareas requieren el modelo más caro. La clasificación de urgencia y tareas simples deben usar el modelo más barato disponible. Solo la generación de insights usa el modelo principal. Documentar el costo promedio por análisis para poder proyectar a escala.

**Sobre la confiabilidad de los agentes:** el Orquestador es código determinista, nunca un LLM. Los agentes fallan silenciosamente — implementar validación de outputs y alertas cuando la tasa de fallos supera el 10%. Todos los estados de los procesos (pending/analyzing/done/failed) deben quedar en la DB para poder debuggear cualquier problema después.

**Sobre los datos de usuarios:** los PDFs subidos por usuarios son datos sensibles. Almacenarlos en R2 con acceso privado (URLs firmadas con expiración). No usar datos de usuarios para entrenar o mejorar modelos sin consentimiento explícito.

**Sobre el plan free:** el plan free tiene valor real — 2 competidores es suficiente para probar el producto. El límite está pensado para que el upgrade sea necesario cuando el producto genera valor, no para bloquear la experiencia desde el inicio.

---

*Especificación MVP — Junio 2026*
