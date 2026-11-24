from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4, uuid7

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from scibiom_core.identity.domain.auth_challenge import MAX_VERIFICATION_ATTEMPTS, AuthChallenge
from scibiom_core.identity.domain.email import Email
from scibiom_infrastructure.database.repositories.identity.challenges import (
    SqlChallengeRepository,
)
from scibiom_infrastructure.database.repositories.identity.transaction import (
    SqlIdentityTransactions,
)
from scibiom_infrastructure.database.tables.identity.auth_challenges import auth_challenges

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID

    from sqlalchemy import Table
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

pytestmark = pytest.mark.integration

type IsRowLocked = Callable[[Table, UUID], Awaitable[bool]]

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
CODE_MAC = b"\x01" * 32


def _email() -> Email:
    return Email(f"{uuid4().hex}@example.com")


def _challenge(email: Email, now: datetime = NOW) -> AuthChallenge:
    return AuthChallenge.issue(uuid7(), email, CODE_MAC, now)


@pytest.fixture
def repository(connection: AsyncConnection) -> SqlChallengeRepository:
    return SqlChallengeRepository(connection)


async def test_challenge_round_trips(repository: SqlChallengeRepository) -> None:
    challenge = _challenge(_email())

    await repository.add(challenge)

    assert await repository.lock_active(challenge.email) == challenge


async def test_lock_active_skips_other_addresses_and_closed_challenges(
    repository: SqlChallengeRepository,
) -> None:
    email = _email()
    for challenge in (
        _challenge(_email()),
        _challenge(email).consume(NOW),
        _challenge(email).invalidate(NOW),
    ):
        await repository.add(challenge)

    assert await repository.lock_active(email) is None


async def test_a_second_active_challenge_for_the_same_address_is_rejected(
    repository: SqlChallengeRepository,
) -> None:
    email = _email()
    await repository.add(_challenge(email))

    with pytest.raises(IntegrityError, match="uq_auth_challenges_one_active"):
        await repository.add(_challenge(email, NOW + timedelta(seconds=1)))


async def test_saved_attempts_and_consumption_are_persisted(
    repository: SqlChallengeRepository,
) -> None:
    challenge = _challenge(_email())
    await repository.add(challenge)
    after_failure = challenge.record_failed_attempt()

    await repository.save(after_failure)

    locked = await repository.lock_active(challenge.email)
    assert locked is not None
    assert locked.attempts_left == MAX_VERIFICATION_ATTEMPTS - 1

    await repository.save(after_failure.consume(NOW))

    assert await repository.lock_active(challenge.email) is None


async def test_invalidate_active_closes_only_the_active_challenge_of_that_address(
    repository: SqlChallengeRepository, connection: AsyncConnection
) -> None:
    email = _email()
    target = _challenge(email)
    other_address = _challenge(_email())
    for challenge in (target, other_address):
        await repository.add(challenge)
    later = NOW + timedelta(minutes=1)

    await repository.invalidate_active(email, later)

    assert await repository.lock_active(email) is None
    assert await repository.lock_active(other_address.email) == other_address
    stored = await connection.execute(
        select(auth_challenges.c.invalidated_at).where(auth_challenges.c.id == target.id)
    )
    assert stored.scalar_one() == later


async def test_issuance_count_covers_every_state_since_the_given_time(
    repository: SqlChallengeRepository,
) -> None:
    email = _email()
    since = NOW + timedelta(minutes=10)
    issued = (
        _challenge(email, since - timedelta(seconds=1)),
        _challenge(email, since).consume(since),
        _challenge(email, since + timedelta(minutes=1)).invalidate(since),
        _challenge(_email(), since),
    )
    for challenge in issued:
        await repository.add(challenge)

    assert await repository.count_issued_since(email, since) == 2


async def test_latest_issue_time_is_the_newest_for_that_address(
    repository: SqlChallengeRepository,
) -> None:
    email = _email()
    assert await repository.latest_issued_at(email) is None
    newest = NOW + timedelta(minutes=2)
    await repository.add(_challenge(email, NOW).invalidate(NOW))
    await repository.add(_challenge(email, newest))
    await repository.add(_challenge(_email(), newest + timedelta(hours=1)))

    assert await repository.latest_issued_at(email) == newest


async def test_lock_holds_the_row_until_the_transaction_ends(
    app_engine: AsyncEngine, is_row_locked: IsRowLocked
) -> None:
    challenge = _challenge(_email())
    transactions = SqlIdentityTransactions(app_engine)
    async with transactions.begin() as setup:
        await setup.challenges.add(challenge)

    async with transactions.begin() as holder:
        await holder.challenges.lock_active(challenge.email)
        assert await is_row_locked(auth_challenges, challenge.id)
    assert not await is_row_locked(auth_challenges, challenge.id)
