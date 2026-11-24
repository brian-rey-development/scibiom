from alembic import context
from sqlalchemy import NullPool, create_engine
from sqlalchemy.schema import CreateSchema

from scibiom_infrastructure.database.settings import MigrationSettings

VERSION_TABLE_SCHEMA = "alembic"


def run_migrations_online() -> None:
    settings = MigrationSettings.model_validate({})
    engine = create_engine(
        settings.database_url.get_secret_value(),
        poolclass=NullPool,
        connect_args={"options": f"-c lock_timeout={settings.lock_timeout_ms}"},
    )
    with engine.connect() as connection:
        connection.execute(CreateSchema(VERSION_TABLE_SCHEMA, if_not_exists=True))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=None,
            include_schemas=True,
            version_table_schema=VERSION_TABLE_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    message = "offline migrations are not supported"
    raise RuntimeError(message)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
