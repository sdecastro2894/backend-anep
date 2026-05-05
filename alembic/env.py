"""
Configuración de Alembic para migraciones automáticas.
Detecta los modelos SQLAlchemy y genera los scripts de migración.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Importar la Base y todos los modelos para que Alembic los detecte
from app.core.database import Base
from app.core.config import settings

# Importar explícitamente todos los modelos (necesario para autogenerate)
import app.models  # noqa: F401

# Configuración de logging de Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos para autogenerate
target_metadata = Base.metadata

# Inyectar la URL de la DB desde la configuración (no desde alembic.ini)
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Modo offline: genera el SQL sin conectarse a la DB.
    Útil para revisar migraciones antes de aplicarlas.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detecta cambios de tipo en columnas
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: se conecta a la DB y aplica las migraciones directamente.
    Usamos create_engine directamente en vez de engine_from_config
    para evitar que lea la URL placeholder del alembic.ini
    """
    from sqlalchemy import create_engine

    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
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