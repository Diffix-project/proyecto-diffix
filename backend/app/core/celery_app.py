"""
Instancia de Celery para vigi.ai.

Beat schedule:
  - Monitoreo diario: todos los días a las 3am hora Argentina.
  - Digest semanal: los lunes a las 9am hora Argentina.

Los módulos de tareas (app.workers.tasks) los crea el agente D.
El include es lazy: Celery los registra al arrancar, no al importar este módulo.
"""

from celery import Celery  # type: ignore[import-untyped]
from celery.schedules import crontab  # type: ignore[import-untyped]

from app.core.config import settings

celery_app = Celery(
    "vigi",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    # Registra las tareas al arrancar el worker/beat.
    # El módulo app.workers.tasks lo crea el agente D; el import es lazy.
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Zona horaria Argentina para que crontab sea correcto
    timezone=settings.timezone,
    enable_utc=True,
    # Serialización segura
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Beat schedule
    beat_schedule={
        "monitoreo-diario-3am-ar": {
            "task": "app.workers.tasks.run_daily_monitoring",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "monitoring"},
        },
        "digest-semanal-lunes-9am-ar": {
            "task": "app.workers.tasks.send_weekly_digests",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),  # 1 = lunes
            "options": {"queue": "notifications"},
        },
    },
)
