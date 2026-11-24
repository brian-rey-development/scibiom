from alembic import context
from sqlalchemy import NullPool, create_engine
from sqlalchemy.schema import CreateSchema

from scibiom_infrastructure.database.settings import MigrationSettings
from scibiom_infrastructure.database.tables.identity.accounts import accounts
from scibiom_infrastructure.database.tables.identity.auth_challenges import auth_challenges
from scibiom_infrastructure.database.tables.identity.metadata import identity_metadata
from scibiom_infrastructure.database.tables.identity.sessions import sessions

VERSION_TABLE_SCHEMA = "alembic"
# Importing each table registers it on the metadata that autogenerate compares against.
MIGRATED_TABLES = (accounts, auth_challenges, sessions)


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
            target_metadata=identity_metadata,
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
