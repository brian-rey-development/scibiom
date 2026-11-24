import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4, uuid7

import psycopg
import pytest
from sqlalchemy import Table, delete, insert, select
from sqlalchemy.exc import IntegrityError

from scibiom_infrastructure.database.tables.identity.accounts import accounts
from scibiom_infrastructure.database.tables.identity.auth_challenges import auth_challenges
from scibiom_infrastructure.database.tables.identity.sessions import sessions

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

pytestmark = pytest.mark.integration

type Row = dict[str, Any]

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
DIGEST = b"\x01" * 32


def _account_row(**overrides: Any) -> Row:  # noqa: ANN401 - overrides take any column value
    return {
        "id": uuid7(),
        "workspace_id": uuid7(),
        "email": f"{uuid4().hex}@example.com",
        "created_at": NOW,
        **overrides,
    }


def _session_row(account_id: UUID, **overrides: Any) -> Row:  # noqa: ANN401
    return {
        "id": uuid7(),
        "account_id": account_id,
        "token_hash": os.urandom(32),
        "created_at": NOW,
        "expires_at": NOW + timedelta(days=14),
        **overrides,
    }


def _challenge_row(**overrides: Any) -> Row:  # noqa: ANN401
    return {
        "id": uuid7(),
        "email": f"{uuid4().hex}@example.com",
        "code_mac": DIGEST,
        "attempts_left": 3,
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "consumed_at": None,
        "invalidated_at": None,
        **overrides,
    }


async def _insert(connection: AsyncConnection, table: Table, row: Row) -> Row:
    await connection.execute(insert(table).values(**row))
    return row


async def _violated_constraint(connection: AsyncConnection, table: Table, row: Row) -> str | None:
    with pytest.raises(IntegrityError) as error:
        await connection.execute(insert(table).values(**row))
    assert isinstance(error.value.orig, psycopg.Error)
    return error.value.orig.diag.constraint_name


async def _count(connection: AsyncConnection, table: Table, **filters: UUID) -> int:
    statement = select(table.c.id).where(
        *(table.c[name] == value for name, value in filters.items())
    )
    return len((await connection.execute(statement)).all())


async def test_valid_rows_are_accepted(connection: AsyncConnection) -> None:
    account = await _insert(connection, accounts, _account_row())
    await _insert(connection, sessions, _session_row(account["id"]))
    await _insert(connection, auth_challenges, _challenge_row())


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param({"email": "Ana@example.com"}, "accounts_email_normalized", id="uppercase"),
        pytest.param({"email": " ana@example.com"}, "accounts_email_normalized", id="padded"),
    ],
)
async def test_accounts_reject_invalid_rows(
    connection: AsyncConnection, overrides: Row, constraint: str
) -> None:
    assert await _violated_constraint(connection, accounts, _account_row(**overrides)) == constraint


async def test_accounts_reject_a_duplicate_email(connection: AsyncConnection) -> None:
    first = await _insert(connection, accounts, _account_row())

    duplicate = _account_row(email=first["email"])

    assert await _violated_constraint(connection, accounts, duplicate) == "accounts_email_key"


async def test_accounts_reject_a_shared_workspace(connection: AsyncConnection) -> None:
    first = await _insert(connection, accounts, _account_row())

    shared = _account_row(workspace_id=first["workspace_id"])

    assert await _violated_constraint(connection, accounts, shared) == "accounts_workspace_id_key"


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param({"token_hash": b"short"}, "sessions_token_hash_length", id="short-hash"),
        pytest.param(
            {"expires_at": NOW}, "sessions_expires_after_created", id="expires-at-creation"
        ),
    ],
)
async def test_sessions_reject_invalid_rows(
    connection: AsyncConnection, overrides: Row, constraint: str
) -> None:
    account = await _insert(connection, accounts, _account_row())

    row = _session_row(account["id"], **overrides)

    assert await _violated_constraint(connection, sessions, row) == constraint


async def test_sessions_reject_an_unknown_account(connection: AsyncConnection) -> None:
    row = _session_row(uuid7())

    assert await _violated_constraint(connection, sessions, row) == "sessions_account_id_fkey"


async def test_sessions_reject_a_duplicate_token_hash(connection: AsyncConnection) -> None:
    account = await _insert(connection, accounts, _account_row())
    first = await _insert(connection, sessions, _session_row(account["id"]))

    duplicate = _session_row(account["id"], token_hash=first["token_hash"])

    assert await _violated_constraint(connection, sessions, duplicate) == "sessions_token_hash_key"


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param({"email": "Ana@example.com"}, "auth_challenges_email_normalized", id="email"),
        pytest.param({"code_mac": b"short"}, "auth_challenges_code_mac_length", id="mac-length"),
        pytest.param({"attempts_left": -1}, "auth_challenges_attempts_left_range", id="negative"),
        pytest.param({"attempts_left": 4}, "auth_challenges_attempts_left_range", id="too-many"),
        pytest.param(
            {"expires_at": NOW}, "auth_challenges_expires_after_created", id="expires-at-creation"
        ),
        pytest.param(
            {"consumed_at": NOW, "invalidated_at": NOW},
            "auth_challenges_not_consumed_and_invalidated",
            id="consumed-and-invalidated",
        ),
    ],
)
async def test_challenges_reject_invalid_rows(
    connection: AsyncConnection, overrides: Row, constraint: str
) -> None:
    row = _challenge_row(**overrides)

    assert await _violated_constraint(connection, auth_challenges, row) == constraint


async def test_deleting_an_account_deletes_its_sessions_only(
    connection: AsyncConnection,
) -> None:
    account = await _insert(connection, accounts, _account_row())
    session = await _insert(connection, sessions, _session_row(account["id"]))
    challenge = await _insert(connection, auth_challenges, _challenge_row(email=account["email"]))

    await connection.execute(delete(accounts).where(accounts.c.id == account["id"]))

    assert await _count(connection, sessions, id=session["id"]) == 0
    assert await _count(connection, auth_challenges, id=challenge["id"]) == 1
