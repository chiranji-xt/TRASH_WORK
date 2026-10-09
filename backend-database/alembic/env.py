"""Alembic environment. Uses DATABASE_URL from backend.config (read from .env)."""
import logging
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure `backend` package is importable (run from backend-database/ dir).
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.config import DATABASE_URL  # noqa: E402
from backend.db import Base  # noqa: E402
import backend.models  # noqa: F401,E402  (register models on Base.metadata)

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

logger = logging.getLogger("alembic.env")
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
