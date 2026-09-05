"""Alembic environment for the small M2 PostgreSQL schema."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from api.app.database import DEFAULT_DATABASE_URL
from api.app.models import Base


config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without connecting, when Alembic is invoked in offline mode."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against the configured PostgreSQL database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
