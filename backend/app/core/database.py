from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Ajuste por driver: psycopg (postgres) vs sqlite (tests)
_is_sqlite = settings.database_url.startswith("sqlite")

connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    # Pool generoso para el worker de Celery; en SQLite no aplica pool.
    pool_pre_ping=True,
)

# Habilitar WAL en SQLite para mayor concurrencia en tests
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI que provee una sesión de DB por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
