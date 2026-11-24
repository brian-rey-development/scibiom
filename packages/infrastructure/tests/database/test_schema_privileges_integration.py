import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.schema import CreateSchema, DropSchema

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

pytestmark = pytest.mark.integration

MIGRATION_STATE_SCHEMA = "alembic"
# A context schema is compliant when scibiom_app can use it, will get row access to future
# tables through default privileges, and already has row access to every existing table.
SCHEMAS_WITHOUT_APP_ACCESS = text("""
    SELECT n.nspname
    FROM pg_namespace AS n
    WHERE n.nspname NOT IN ('public', 'information_schema', :migration_state)
      AND n.nspname NOT LIKE 'pg\\_%'
      AND (
        NOT has_schema_privilege('scibiom_app', n.oid, 'USAGE')
        OR NOT EXISTS (
          SELECT 1
          FROM pg_default_acl AS d, aclexplode(d.defaclacl) AS acl
          WHERE d.defaclnamespace = n.oid
            AND d.defaclobjtype = 'r'
            AND acl.grantee = 'scibiom_app'::regrole
        )
        OR EXISTS (
          SELECT 1
          FROM pg_class AS c
          WHERE c.relnamespace = n.oid
            AND c.relkind IN ('r', 'p')
            AND NOT has_table_privilege('scibiom_app', c.oid, 'SELECT, INSERT, UPDATE, DELETE')
        )
      )
""")
type GrantAppAccess = Callable[[AsyncConnection, str], Awaitable[None]]


async def _schemas_without_app_access(connection: AsyncConnection) -> set[str]:
    result = await connection.execute(
        SCHEMAS_WITHOUT_APP_ACCESS, {"migration_state": MIGRATION_STATE_SCHEMA}
    )
    return set(result.scalars())


@asynccontextmanager
async def _scratch_schema(engine: AsyncEngine, grant: GrantAppAccess | None) -> AsyncGenerator[str]:
    schema = f"scratch_{uuid.uuid4().hex}"
    async with engine.begin() as connection:
        await connection.execute(CreateSchema(schema))
        if grant is not None:
            await grant(connection, schema)
    try:
        yield schema
    finally:
        async with engine.begin() as connection:
            await connection.execute(DropSchema(schema, cascade=True))


@pytest.fixture
async def granted_schema(
    owner_engine: AsyncEngine, grant_app_access: GrantAppAccess
) -> AsyncIterator[str]:
    async with _scratch_schema(owner_engine, grant_app_access) as schema:
        yield schema


@pytest.fixture
async def ungranted_schema(owner_engine: AsyncEngine) -> AsyncIterator[str]:
    async with _scratch_schema(owner_engine, None) as schema:
        yield schema


async def test_every_migrated_context_schema_grants_the_app_role_access(
    owner_engine: AsyncEngine,
) -> None:
    async with owner_engine.connect() as connection:
        missing = await _schemas_without_app_access(connection)

    assert missing == set()


async def test_guard_flags_a_schema_created_without_grants(
    owner_engine: AsyncEngine, granted_schema: str, ungranted_schema: str
) -> None:
    async with owner_engine.connect() as connection:
        missing = await _schemas_without_app_access(connection)

    assert ungranted_schema in missing
    assert granted_schema not in missing


async def test_app_role_has_no_access_to_migration_state(owner_engine: AsyncEngine) -> None:
    async with owner_engine.connect() as connection:
        result = await connection.execute(
            text("SELECT has_schema_privilege('scibiom_app', :schema, 'USAGE')"),
            {"schema": MIGRATION_STATE_SCHEMA},
        )

    assert result.scalar_one() is False
