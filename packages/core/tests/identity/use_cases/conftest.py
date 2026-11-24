from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from scibiom_core.kernel.access import Actor

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from uuid import UUID

    from scibiom_core.identity.domain.account import Account
    from scibiom_core.identity.domain.auth_challenge import AuthChallenge
    from scibiom_core.identity.domain.email import Email
    from scibiom_core.identity.domain.session import Session
    from scibiom_core.identity.ports.email_sender import EmailMessage
    from scibiom_core.kernel.errors import UnavailableError

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


class ActiveChallengeExistsError(Exception):
    """The fake database's unique index on active challenges per address."""


@dataclass(slots=True)
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class FakeEmailSender:
    def __init__(self) -> None:
        self.failure: UnavailableError | None = None
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        if self.failure is not None:
            raise self.failure
        self.sent.append(message)


class FakeChallenges:
    def __init__(self) -> None:
        self.rows: dict[UUID, AuthChallenge] = {}

    def _active(self, email: Email) -> list[AuthChallenge]:
        return [
            row
            for row in self.rows.values()
            if row.email == email and row.consumed_at is None and row.invalidated_at is None
        ]

    async def add(self, challenge: AuthChallenge) -> None:
        if self._active(challenge.email):
            raise ActiveChallengeExistsError
        self.rows[challenge.id] = challenge

    async def lock_active(self, email: Email) -> AuthChallenge | None:
        return next(iter(self._active(email)), None)

    async def save(self, challenge: AuthChallenge) -> None:
        self.rows[challenge.id] = challenge

    async def invalidate_active(self, email: Email, now: datetime) -> None:
        for row in self._active(email):
            self.rows[row.id] = row.invalidate(now)

    async def count_issued_since(self, email: Email, since: datetime) -> int:
        return sum(row.email == email and row.created_at >= since for row in self.rows.values())

    async def latest_issued_at(self, email: Email) -> datetime | None:
        return max(
            (row.created_at for row in self.rows.values() if row.email == email), default=None
        )


class FakeAccounts:
    def __init__(self) -> None:
        self.rows: dict[UUID, Account] = {}

    async def find_by_email(self, email: Email) -> Account | None:
        return next((row for row in self.rows.values() if row.email == email), None)

    async def find_by_id(self, account_id: UUID) -> Account | None:
        return self.rows.get(account_id)

    async def add(self, account: Account) -> None:
        self.rows[account.id] = account


class FakeSessions:
    def __init__(self, accounts: FakeAccounts) -> None:
        self.accounts = accounts
        self.rows: dict[bytes, Session] = {}

    async def add(self, session: Session) -> None:
        self.rows[session.token_hash] = session

    async def find_with_actor(self, token_hash: bytes) -> tuple[Session, Actor] | None:
        session = self.rows.get(token_hash)
        if session is None:
            return None
        account = self.accounts.rows[session.account_id]
        return session, Actor(account.id, account.workspace_id)

    async def delete_by_token_hash(self, token_hash: bytes) -> None:
        self.rows.pop(token_hash, None)


@dataclass(slots=True)
class FakeIdentityTransaction:
    accounts: FakeAccounts
    challenges: FakeChallenges
    sessions: FakeSessions
    locked_emails: list[Email]

    async def lock_email(self, email: Email) -> None:
        self.locked_emails.append(email)


class FakeIdentityTransactions:
    def __init__(self) -> None:
        self.accounts = FakeAccounts()
        self.challenges = FakeChallenges()
        self.sessions = FakeSessions(self.accounts)
        self.locked_emails: list[Email] = []

    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[FakeIdentityTransaction]:
        committed = (
            dict(self.accounts.rows),
            dict(self.challenges.rows),
            dict(self.sessions.rows),
        )
        try:
            yield FakeIdentityTransaction(
                self.accounts, self.challenges, self.sessions, self.locked_emails
            )
        except BaseException:
            self.accounts.rows, self.challenges.rows, self.sessions.rows = committed
            raise


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(NOW)


@pytest.fixture
def email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def transactions() -> FakeIdentityTransactions:
    return FakeIdentityTransactions()
