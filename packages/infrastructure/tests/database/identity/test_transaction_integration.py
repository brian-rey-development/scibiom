import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import text

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email
from scibiom_infrastructure.database.repositories.identity.accounts import SqlAccountRepository
from scibiom_infrastructure.database.repositories.identity.transaction import (
    SqlIdentityTransactions,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
WAIT_SECONDS = 5
POLL_SECONDS = 0.02
NOT_BLOCKED_SECONDS = 2
ADVISORY_LOCK_WAITERS = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE wait_event_type = 'Lock' AND wait_event = 'advisory'"
)


class _Abort(Exception):  # noqa: N818 - a test signal, not an error type
    pass


def _email() -> Email:
    return Email(f"{uuid4().hex}@example.com")


async def _wait_for_an_advisory_lock_waiter(engine: AsyncEngine) -> None:
    async with asyncio.timeout(WAIT_SECONDS):
        while True:
            async with engine.connect() as connection:
                if (await connection.execute(ADVISORY_LOCK_WAITERS)).scalar_one() > 0:
                    return
            await asyncio.sleep(POLL_SECONDS)


async def _find(engine: AsyncEngine, account: Account) -> Account | None:
    async with engine.connect() as connection:
        return await SqlAccountRepository(connection).find_by_id(account.id)


async def test_normal_exit_commits_the_work_of_every_repository(app_engine: AsyncEngine) -> None:
    account = Account.register(_email(), NOW)
    transactions = SqlIdentityTransactions(app_engine)

    async with transactions.begin() as transaction:
        await transaction.accounts.add(account)

    assert await _find(app_engine, account) == account


async def _add_then_abort(engine: AsyncEngine, account: Account) -> None:
    async with SqlIdentityTransactions(engine).begin() as transaction:
        await transaction.accounts.add(account)
        raise _Abort


async def test_an_exception_rolls_the_transaction_back(app_engine: AsyncEngine) -> None:
    account = Account.register(_email(), NOW)

    with pytest.raises(_Abort):
        await _add_then_abort(app_engine, account)

    assert await _find(app_engine, account) is None


async def test_lock_email_makes_a_second_transaction_on_the_same_address_wait(
    app_engine: AsyncEngine,
) -> None:
    transactions = SqlIdentityTransactions(app_engine)
    email = _email()

    async def lock_in_a_second_transaction() -> None:
        async with transactions.begin() as second:
            await second.lock_email(email)

    async with transactions.begin() as first:
        await first.lock_email(email)
        second_task = asyncio.create_task(lock_in_a_second_transaction())
        await _wait_for_an_advisory_lock_waiter(app_engine)
        assert not second_task.done()

    await asyncio.wait_for(second_task, timeout=WAIT_SECONDS)


async def test_lock_email_does_not_block_other_addresses(app_engine: AsyncEngine) -> None:
    transactions = SqlIdentityTransactions(app_engine)

    async with transactions.begin() as first:
        await first.lock_email(_email())
        async with asyncio.timeout(NOT_BLOCKED_SECONDS), transactions.begin() as second:
            await second.lock_email(_email())
