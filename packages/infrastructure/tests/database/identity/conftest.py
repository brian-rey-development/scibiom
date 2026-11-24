from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable
    from uuid import UUID

    from sqlalchemy import Table
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

type IsRowLocked = Callable[[Table, UUID], Awaitable[bool]]


@pytest.fixture
async def connection(app_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """A connection whose uncommitted work is discarded when the test ends."""
    async with app_engine.connect() as connection:
        yield connection


@pytest.fixture
def is_row_locked(app_engine: AsyncEngine) -> IsRowLocked:
    async def probe(table: Table, row_id: UUID) -> bool:
        statement = table.select().where(table.c.id == row_id).with_for_update(skip_locked=True)
        async with app_engine.begin() as other_connection:
            return (await other_connection.execute(statement)).first() is None

    return probe
