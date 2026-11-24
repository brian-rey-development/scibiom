from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import create_async_engine

from scibiom_infrastructure.database.engine import create_database_engine
from scibiom_infrastructure.database.settings import DatabaseSettings, MigrationSettings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

UNREACHABLE_URL = "postgresql+psycopg://user:unreachable-secret@127.0.0.1:1/db"
UNREACHABLE_CONNECT_TIMEOUT_SECONDS = 1
# The statements every migration that creates a context schema runs, as documented in AGENTS.md.
APP_ACCESS_GRANTS = (
    "GRANT USAGE ON SCHEMA {schema} TO scibiom_app",
    (
        "ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scibiom_app"
    ),
)


type GrantAppAccess = Callable[[AsyncConnection, str], Awaitable[None]]


async def _grant_app_access(connection: AsyncConnection, schema: str) -> None:
    for statement in APP_ACCESS_GRANTS:
        await connection.execute(text(statement.format(schema=schema)))


@pytest.fixture
def grant_app_access() -> GrantAppAccess:
    return _grant_app_access


class _IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIBIOM_", env_file=".env", env_nested_delimiter="__", extra="ignore"
    )

    database: DatabaseSettings


@pytest.fixture
def database_settings() -> DatabaseSettings:
    return _IntegrationSettings.model_validate({}).database


@pytest.fixture
async def app_engine(database_settings: DatabaseSettings) -> AsyncIterator[AsyncEngine]:
    engine = create_database_engine(database_settings)
    yield engine
    await engine.dispose()


@pytest.fixture
async def owner_engine() -> AsyncIterator[AsyncEngine]:
    owner_url = MigrationSettings.model_validate({}).database_url.get_secret_value()
    engine = create_async_engine(owner_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def unreachable_engine() -> AsyncIterator[AsyncEngine]:
    settings = DatabaseSettings(
        url=SecretStr(UNREACHABLE_URL), connect_timeout_seconds=UNREACHABLE_CONNECT_TIMEOUT_SECONDS
    )
    engine = create_database_engine(settings)
    yield engine
    await engine.dispose()
