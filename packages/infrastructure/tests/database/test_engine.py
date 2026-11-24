from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from scibiom_infrastructure.database.engine import create_database_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine

    from scibiom_infrastructure.database.settings import DatabaseSettings

PARAMETER_VALUE = "patient-123-secret"
SINGLE_CONNECTION_POOL_TIMEOUT_SECONDS = 0.1


async def test_connection_errors_do_not_reveal_the_password(
    unreachable_engine: AsyncEngine,
) -> None:
    password = unreachable_engine.url.password
    assert password is not None

    with pytest.raises(OperationalError) as excinfo:
        async with unreachable_engine.connect():
            pass

    assert password not in str(excinfo.value)


@pytest.fixture
async def single_connection_engine(
    database_settings: DatabaseSettings,
) -> AsyncIterator[AsyncEngine]:
    settings = database_settings.model_copy(
        update={
            "pool_size": 1,
            "max_overflow": 0,
            "pool_timeout_seconds": SINGLE_CONNECTION_POOL_TIMEOUT_SECONDS,
        }
    )
    engine = create_database_engine(settings)
    yield engine
    await engine.dispose()


@pytest.mark.integration
async def test_statement_errors_do_not_reveal_parameter_values(app_engine: AsyncEngine) -> None:
    async with app_engine.connect() as connection:
        with pytest.raises(DBAPIError) as excinfo:
            await connection.execute(
                text("SELECT CAST(:value AS text), 1 / 0"), {"value": PARAMETER_VALUE}
            )

    assert PARAMETER_VALUE not in str(excinfo.value)


@pytest.mark.integration
async def test_statement_timeout_matches_settings(
    app_engine: AsyncEngine, database_settings: DatabaseSettings
) -> None:
    async with app_engine.connect() as connection:
        result = await connection.execute(
            text("SELECT setting::int FROM pg_settings WHERE name = 'statement_timeout'")
        )

    assert result.scalar_one() == database_settings.statement_timeout_ms


@pytest.mark.integration
async def test_exhausted_pool_fails_after_the_configured_timeout(
    single_connection_engine: AsyncEngine,
) -> None:
    async with single_connection_engine.connect():
        with pytest.raises(PoolTimeoutError):
            async with single_connection_engine.connect():
                pass
