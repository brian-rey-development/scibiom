import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, delete, insert, select, text, update
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.schema import CreateSchema, DropSchema

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

pytestmark = pytest.mark.integration

type GrantAppAccess = Callable[[AsyncConnection, str], Awaitable[None]]

APP_ROLE = "scibiom_app"
PERMISSION_DENIED = "permission denied"
DDL_TEMPLATES = (
    "CREATE TABLE public.should_fail (id int)",
    "CREATE TABLE {schema}.should_fail (id int)",
)
MIGRATION_STATE_STATEMENTS = (
    "SELECT version_num FROM alembic.alembic_version",
    "DELETE FROM alembic.alembic_version",
)


@pytest.fixture
async def owner_table(
    owner_engine: AsyncEngine,
    grant_app_access: GrantAppAccess,
) -> AsyncIterator[Table]:
    schema = f"scratch_{uuid.uuid4().hex}"
    note = Table("note", MetaData(schema=schema), Column("id", Integer))
    async with owner_engine.begin() as connection:
        await connection.execute(CreateSchema(schema))
        await grant_app_access(connection, schema)
        await connection.run_sync(note.metadata.create_all)
    yield note
    async with owner_engine.begin() as connection:
        await connection.execute(DropSchema(schema, cascade=True, if_exists=True))


async def test_sessions_connect_as_the_app_role(app_engine: AsyncEngine) -> None:
    async with app_engine.connect() as connection:
        result = await connection.execute(text("SELECT current_user"))

    assert result.scalar_one() == APP_ROLE


async def test_app_role_can_read_and_write_tables_in_a_schema_that_grants_it_access(
    app_engine: AsyncEngine, owner_table: Table
) -> None:
    async with app_engine.connect() as connection:
        await connection.execute(insert(owner_table).values(id=1))
        await connection.execute(update(owner_table).values(id=2))
        selected = await connection.execute(select(owner_table.c.id))
        await connection.execute(delete(owner_table))

    assert selected.scalar_one() == 2


@pytest.mark.parametrize("template", DDL_TEMPLATES)
async def test_app_role_cannot_run_ddl(
    app_engine: AsyncEngine, owner_table: Table, template: str
) -> None:
    statement = template.format(schema=owner_table.schema)

    async with app_engine.connect() as connection:
        with pytest.raises(ProgrammingError, match=PERMISSION_DENIED):
            await connection.execute(text(statement))


@pytest.mark.parametrize("statement", MIGRATION_STATE_STATEMENTS)
async def test_app_role_cannot_touch_migration_state(
    app_engine: AsyncEngine, statement: str
) -> None:
    async with app_engine.connect() as connection:
        with pytest.raises(ProgrammingError, match=PERMISSION_DENIED):
            await connection.execute(text(statement))
