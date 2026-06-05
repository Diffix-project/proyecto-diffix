"""
Tareas Celery de vigi.ai.

Todas las tareas son placeholders idempotentes en esta fase (Fundación).
El cuerpo real de cada una se completa en las fases indicadas en los docstrings.

Nombres exactos requeridos por celery_app.beat_schedule:
  - app.workers.tasks.run_daily_monitoring
  - app.workers.tasks.send_weekly_digests
"""

import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.run_daily_monitoring", bind=True)
def run_daily_monitoring(self):  # type: ignore[no-untyped-def]
    """
    Orquestador del monitoreo diario (Celery Beat: 3am hora Argentina).

    Consulta todos los competidores activos y encola una tarea scout_competitor
    por cada uno. En esta fase (Fundación) solo logea el conteo y encola los stubs.

    Fase real: Scout Agent.
    """
    db = SessionLocal()
    try:
        # Import aquí para evitar circular imports al nivel de módulo
        from app.domains.competitors.models import Competitor  # noqa: PLC0415

        active = db.query(Competitor.id).filter(Competitor.is_active.is_(True)).all()
        count = len(active)
        logger.info("run_daily_monitoring: %d competidores activos encontrados", count)

        for (competitor_id,) in active:
            scout_competitor.delay(str(competitor_id))
            logger.debug("run_daily_monitoring: encolado scout_competitor id=%s", competitor_id)

        logger.info("run_daily_monitoring: %d tareas scout_competitor encoladas", count)
    except Exception as exc:
        logger.error("run_daily_monitoring: error inesperado: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.scout_competitor", bind=True)
def scout_competitor(self, competitor_id: str):  # type: ignore[no-untyped-def]
    """
    Monitorea un competidor: obtiene estado de cada fuente, compara hash SHA256
    con el snapshot anterior y guarda un Change si hay diferencias significativas.

    TODO (fase Scout): implementar lógica completa del Scout Agent:
      - Llamar a integrations.scraper.fetch_clean_text para fuentes web
      - Llamar a integrations.mercadolibre.get_seller_state para fuentes ML
      - Llamar a integrations.apify.get_job_postings para fuentes de jobs
      - Comparar hash SHA256 con snapshot anterior
      - Guardar Snapshot + Change en DB si hay diff significativo
      - Encolar analyze_change.delay(change_id) para cada Change nuevo
      - Un error en una fuente NO debe detener el resto
    """
    logger.info("scout_competitor [placeholder] competitor_id=%s", competitor_id)
    # TODO: fase Scout


@celery_app.task(name="app.workers.tasks.analyze_change", bind=True)
def analyze_change(self, change_id: str):  # type: ignore[no-untyped-def]
    """
    Analyst Agent: recibe un change_id, construye prompt con contexto del competidor
    y el rubro, llama al LLM via integrations.llm.complete_json, valida los 4 campos
    requeridos (what_changed, why_it_matters, what_to_do, urgency) y guarda el Insight.

    TODO (fase Analyst): implementar lógica completa del Analyst Agent:
      - Leer Change de la DB, actualizar status a 'analyzing'
      - Construir prompt con diff + nombre competidor + rubro empresa
      - Llamar a integrations.llm.complete_json (temp=0.3, model=settings.llm_model)
      - Validar JSON: 4 campos, urgency in {'alta','media','baja'}, campos no vacíos
      - Reintentar hasta 2 veces si falla validación; marcar 'failed' tras 3 intentos
      - Guardar Insight con langfuse_trace_id
      - Si urgency == 'alta': encolar notify_instant.delay(insight_id)
    """
    logger.info("analyze_change [placeholder] change_id=%s", change_id)
    # TODO: fase Analyst


@celery_app.task(name="app.workers.tasks.notify_instant", bind=True)
def notify_instant(self, insight_id: str):  # type: ignore[no-untyped-def]
    """
    Envía notificación instantánea (email + WhatsApp) cuando un insight tiene
    urgencia 'alta'. Debe completarse en menos de 2 minutos desde la detección.

    TODO (fase Notificaciones): implementar envío real:
      - Leer Insight + Competitor + User de la DB
      - Si notif_email_instant activo: llamar integrations.email.send_email
      - Si notif_whatsapp activo y whatsapp_number configurado: llamar
        integrations.whatsapp.send_whatsapp
      - Registrar Notification en DB con status sent/failed
    """
    logger.info("notify_instant [placeholder] insight_id=%s", insight_id)
    # TODO: fase Notificaciones


@celery_app.task(name="app.workers.tasks.send_weekly_digests", bind=True)
def send_weekly_digests(self):  # type: ignore[no-untyped-def]
    """
    Digest semanal (Celery Beat: lunes 9am hora Argentina).

    Envía un resumen con los 3-5 insights más relevantes de la semana a cada
    usuario activo que tenga notif_email_digest activado.
    Si el usuario no tuvo insights esa semana, no se envía el digest.

    TODO (fase Notificaciones): implementar digest semanal:
      - Consultar usuarios con notif_email_digest=True
      - Para cada usuario: obtener insights de los últimos 7 días, ordenados por urgencia
      - Si 0 insights: skip
      - Construir HTML del digest (3-5 insights agrupados por competidor)
      - Llamar integrations.email.send_email
      - Guardar Digest en DB con status sent/failed
    """
    logger.info("send_weekly_digests [placeholder] iniciando")
    # TODO: fase Notificaciones


@celery_app.task(name="app.workers.tasks.parse_pdf", bind=True)
def parse_pdf(self, source_id: str, snapshot_key: str):  # type: ignore[no-untyped-def]
    """
    Extrae texto de un PDF almacenado en R2 y lo procesa como snapshot.

    Encolada desde el endpoint POST /uploads/pdf tras crear la CompetitorSource.

    TODO (fase Analyst): implementar extracción y comparación:
      - Descargar PDF de R2 via integrations.storage.generate_presigned_url
      - Extraer texto con LLM (integrations.llm.complete_json o herramienta de parsing)
      - Comparar hash SHA256 con snapshot anterior de la misma fuente (source_id)
      - Si hay diff significativo: crear Snapshot + Change en DB
      - Encolar analyze_change.delay(change_id)
    """
    logger.info(
        "parse_pdf [placeholder] source_id=%s snapshot_key=%s",
        source_id,
        snapshot_key,
    )
    # TODO: fase Analyst
