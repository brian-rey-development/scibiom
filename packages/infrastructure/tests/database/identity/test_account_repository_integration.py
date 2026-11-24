from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4, uuid7

import pytest

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email
from scibiom_infrastructure.database.repositories.identity.accounts import SqlAccountRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def _account() -> Account:
    return Account.register(Email(f"{uuid4().hex}@example.com"), NOW)


@pytest.fixture
def repository(connection: AsyncConnection) -> SqlAccountRepository:
    return SqlAccountRepository(connection)


async def test_added_account_is_found_by_email_and_by_id(repository: SqlAccountRepository) -> None:
    account = _account()

    await repository.add(account)

    assert await repository.find_by_email(account.email) == account
    assert await repository.find_by_id(account.id) == account


async def test_unknown_account_is_not_found(repository: SqlAccountRepository) -> None:
    assert await repository.find_by_email(_account().email) is None
    assert await repository.find_by_id(uuid7()) is None
