"""
Alembic env.py — configuración de migraciones para vigi.ai.

- Toma la URL de database_url desde app.core.config.settings.
- Importa todos los módulos de modelos para registrarlos en Base.metadata.
- En migraciones online (Postgres), ejecuta CREATE EXTENSION IF NOT EXISTS vector
  antes de crear tablas.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# ─── Cargar configuración de logging desde alembic.ini ───────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── Importar settings y sobreescribir la URL ────────────────────────────────
from app.core.config import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", settings.database_url)

# ─── Importar todos los modelos para registrar sus tablas en metadata ─────────
# app.models centraliza los 7 modelos. Este import es CRÍTICO: sin él,
# autogenerate no detecta las tablas y los mappers no resuelven sus relaciones.
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


def _is_postgres(connection) -> bool:  # type: ignore[no-untyped-def]
    return connection.dialect.name == "postgresql"


def run_migrations_offline() -> None:
    """Modo offline: genera SQL sin conectar a la DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: conecta a la DB y aplica migraciones."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Habilitar extensión pgvector solo en Postgres
        if _is_postgres(connection):
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
