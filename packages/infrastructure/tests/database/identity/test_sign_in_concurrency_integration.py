import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4, uuid7

import pytest
from sqlalchemy import func, select

from scibiom_core.identity.domain.auth_challenge import AuthChallenge
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.verification_code import code_mac
from scibiom_core.identity.use_cases.verify_sign_in_code import VerifySignInCode
from scibiom_core.kernel.clock import SystemClock
from scibiom_core.kernel.errors import AuthenticationError
from scibiom_infrastructure.database.engine import create_database_engine
from scibiom_infrastructure.database.repositories.identity.transaction import (
    SqlIdentityTransactions,
)
from scibiom_infrastructure.database.tables.identity.accounts import accounts
from scibiom_infrastructure.database.tables.identity.auth_challenges import auth_challenges
from scibiom_infrastructure.database.tables.identity.sessions import sessions

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncEngine

    from scibiom_infrastructure.database.settings import DatabaseSettings

pytestmark = pytest.mark.integration

CONCURRENT_CALLS = 16
TIMEOUT_SECONDS = 20
CODE_SECRET = b"c" * 32
CODE = "482913"
WRONG_CODE = "000000"


@pytest.fixture
async def concurrent_engine(database_settings: DatabaseSettings) -> AsyncIterator[AsyncEngine]:
    settings = database_settings.model_copy(
        update={"pool_size": CONCURRENT_CALLS, "max_overflow": 0}
    )
    engine = create_database_engine(settings)
    yield engine
    await engine.dispose()


async def _issue_challenge(engine: AsyncEngine, email: Email) -> AuthChallenge:
    challenge_id = uuid7()
    mac = code_mac(CODE_SECRET, challenge_id, CODE)
    challenge = AuthChallenge.issue(challenge_id, email, mac, SystemClock().now())
    async with SqlIdentityTransactions(engine).begin() as transaction:
        await transaction.challenges.add(challenge)
    return challenge


async def _verify_concurrently(
    engine: AsyncEngine, email: Email, code: str
) -> list[str | BaseException]:
    verify = VerifySignInCode(SqlIdentityTransactions(engine), SystemClock(), CODE_SECRET)
    async with asyncio.timeout(TIMEOUT_SECONDS):
        return await asyncio.gather(
            *(verify(email.value, code) for _ in range(CONCURRENT_CALLS)), return_exceptions=True
        )


async def _scalar(engine: AsyncEngine, statement: Select[int]) -> int:
    async with engine.connect() as connection:
        return (await connection.execute(statement)).scalar_one()


async def test_concurrent_wrong_codes_spend_exactly_the_attempts_of_the_challenge(
    concurrent_engine: AsyncEngine,
) -> None:
    email = Email(f"{uuid4().hex}@example.com")
    challenge = await _issue_challenge(concurrent_engine, email)

    outcomes = await _verify_concurrently(concurrent_engine, email, WRONG_CODE)

    attempts_left = select(auth_challenges.c.attempts_left).where(
        auth_challenges.c.id == challenge.id
    )
    assert all(type(outcome) is AuthenticationError for outcome in outcomes)
    assert await _scalar(concurrent_engine, attempts_left) == 0


async def test_concurrent_right_codes_create_one_session_and_one_account(
    concurrent_engine: AsyncEngine,
) -> None:
    email = Email(f"{uuid4().hex}@example.com")
    await _issue_challenge(concurrent_engine, email)

    outcomes = await _verify_concurrently(concurrent_engine, email, CODE)

    tokens = [outcome for outcome in outcomes if isinstance(outcome, str)]
    failures = [outcome for outcome in outcomes if type(outcome) is AuthenticationError]
    assert len(tokens) == 1
    assert len(failures) == CONCURRENT_CALLS - 1
    account_count = select(func.count()).where(accounts.c.email == email.value)
    session_count = (
        select(func.count())
        .select_from(sessions)
        .join(accounts, accounts.c.id == sessions.c.account_id)
        .where(accounts.c.email == email.value)
    )
    assert await _scalar(concurrent_engine, account_count) == 1
    assert await _scalar(concurrent_engine, session_count) == 1
