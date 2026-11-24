import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.session import Session
from scibiom_core.kernel.access import Actor
from scibiom_infrastructure.database.repositories.identity.accounts import SqlAccountRepository
from scibiom_infrastructure.database.repositories.identity.sessions import SqlSessionRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


@pytest.fixture
async def account(connection: AsyncConnection) -> Account:
    account = Account.register(Email(f"{uuid4().hex}@example.com"), NOW)
    await SqlAccountRepository(connection).add(account)
    return account


@pytest.fixture
def repository(connection: AsyncConnection) -> SqlSessionRepository:
    return SqlSessionRepository(connection)


def _session(account: Account) -> Session:
    return Session.start(account.id, os.urandom(32), NOW)


async def test_added_session_is_found_with_the_actor_of_its_account(
    repository: SqlSessionRepository, account: Account
) -> None:
    session = _session(account)

    await repository.add(session)

    found = await repository.find_with_actor(session.token_hash)
    assert found == (session, Actor(account.id, account.workspace_id))


async def test_each_session_resolves_to_the_workspace_of_its_own_account(
    repository: SqlSessionRepository, connection: AsyncConnection, account: Account
) -> None:
    other = Account.register(Email(f"{uuid4().hex}@example.com"), NOW)
    await SqlAccountRepository(connection).add(other)
    mine, theirs = _session(account), _session(other)
    await repository.add(mine)
    await repository.add(theirs)

    found = await repository.find_with_actor(theirs.token_hash)

    assert found == (theirs, Actor(other.id, other.workspace_id))


async def test_unknown_token_hash_finds_nothing(repository: SqlSessionRepository) -> None:
    assert await repository.find_with_actor(os.urandom(32)) is None


async def test_deleted_session_is_gone_and_others_remain(
    repository: SqlSessionRepository, account: Account
) -> None:
    deleted, kept = _session(account), _session(account)
    await repository.add(deleted)
    await repository.add(kept)

    await repository.delete_by_token_hash(deleted.token_hash)

    assert await repository.find_with_actor(deleted.token_hash) is None
    found = await repository.find_with_actor(kept.token_hash)
    assert found is not None
    assert found[0] == kept


async def test_deleting_a_missing_session_does_nothing(repository: SqlSessionRepository) -> None:
    await repository.delete_by_token_hash(os.urandom(32))
