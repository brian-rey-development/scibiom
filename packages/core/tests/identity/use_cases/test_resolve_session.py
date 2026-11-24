from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.session import SESSION_LIFETIME, Session, hash_session_token
from scibiom_core.identity.use_cases.resolve_session import ResolveSession
from scibiom_core.kernel.access import Actor
from scibiom_core.kernel.errors import AuthenticationError

if TYPE_CHECKING:
    from conftest import FakeClock, FakeIdentityTransactions

SESSION_VALUE = "opaque-session-token"
UNKNOWN_VALUE = "another-token"
MICROSECOND = timedelta(microseconds=1)


@pytest.fixture
def resolve_session(transactions: FakeIdentityTransactions, clock: FakeClock) -> ResolveSession:
    return ResolveSession(transactions, clock)


def _seed_session(transactions: FakeIdentityTransactions, clock: FakeClock) -> Account:
    account = Account.register(Email("ana@example.com"), clock.now())
    transactions.accounts.rows[account.id] = account
    session = Session.start(account.id, hash_session_token(SESSION_VALUE), clock.now())
    transactions.sessions.rows[session.token_hash] = session
    return account


async def test_a_valid_session_resolves_to_the_actor_of_its_account(
    resolve_session: ResolveSession,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    account = _seed_session(transactions, clock)
    clock.advance(SESSION_LIFETIME - MICROSECOND)

    actor = await resolve_session(SESSION_VALUE)

    assert actor == Actor(account.id, account.workspace_id)


async def test_a_session_is_rejected_from_the_instant_it_expires(
    resolve_session: ResolveSession,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    _seed_session(transactions, clock)
    clock.advance(SESSION_LIFETIME)

    with pytest.raises(AuthenticationError):
        await resolve_session(SESSION_VALUE)


async def test_an_unknown_token_is_rejected(
    resolve_session: ResolveSession,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    _seed_session(transactions, clock)

    with pytest.raises(AuthenticationError):
        await resolve_session(UNKNOWN_VALUE)
