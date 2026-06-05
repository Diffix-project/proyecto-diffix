"""
Punto único de importación de todos los modelos SQLAlchemy del proyecto.

Importar desde acá (o importar este módulo entero) garantiza que las 7 tablas
queden registradas en Base.metadata y que todas las clases referenciadas por
nombre en relationship() existan en el registry antes de configurar los mappers.

Sin esto, importar un subconjunto de modelos y luego ejecutar una query o
configure_mappers() falla con InvalidRequestError (ej.: User.notifications no
resuelve 'Notification' si app.domains.notifications.models nunca se importó).

Usar en:
- alembic/env.py — para que autogenerate detecte todas las tablas.
- scripts y entrypoints que tocan la DB — para registrar el modelo completo.
"""

from app.core.base import Base
from app.domains.auth.models import Company, User
from app.domains.changes.models import Change, Snapshot
from app.domains.competitors.models import Competitor
from app.domains.digests.models import Digest
from app.domains.insights.models import Insight
from app.domains.notifications.models import Notification
from app.domains.sources.models import CompetitorSource

__all__ = [
    "Base",
    "Change",
    "Company",
    "Competitor",
    "CompetitorSource",
    "Digest",
    "Insight",
    "Notification",
    "Snapshot",
    "User",
]
