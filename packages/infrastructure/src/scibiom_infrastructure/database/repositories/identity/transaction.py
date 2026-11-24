from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from scibiom_infrastructure.database.repositories.identity.accounts import SqlAccountRepository
from scibiom_infrastructure.database.repositories.identity.challenges import SqlChallengeRepository
from scibiom_infrastructure.database.repositories.identity.sessions import SqlSessionRepository

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

    from scibiom_core.identity.domain.email import Email

LOCK_EMAIL = text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))")


@dataclass(frozen=True, slots=True)
class SqlIdentityTransaction:
    connection: AsyncConnection
    accounts: SqlAccountRepository
    challenges: SqlChallengeRepository
    sessions: SqlSessionRepository

    async def lock_email(self, email: Email) -> None:
        await self.connection.execute(LOCK_EMAIL, {"email": email.value})


@dataclass(frozen=True, slots=True)
class SqlIdentityTransactions:
    engine: AsyncEngine

    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[SqlIdentityTransaction]:
        async with self.engine.begin() as connection:
            yield SqlIdentityTransaction(
                connection=connection,
                accounts=SqlAccountRepository(connection),
                challenges=SqlChallengeRepository(connection),
                sessions=SqlSessionRepository(connection),
            )
