from typing import TYPE_CHECKING
from uuid import uuid7

import pytest

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.auth_challenge import (
    CHALLENGE_VALIDITY,
    MAX_VERIFICATION_ATTEMPTS,
    AuthChallenge,
)
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.session import SESSION_LIFETIME, hash_session_token
from scibiom_core.identity.domain.verification_code import code_mac
from scibiom_core.identity.use_cases.verify_sign_in_code import (
    SIGN_IN_FAILED_MESSAGE,
    VerifySignInCode,
)
from scibiom_core.kernel.errors import AuthenticationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import FakeClock, FakeIdentityTransactions

CODE_SECRET = b"c" * 32
ADDRESS = "ana@example.com"
EMAIL = Email(ADDRESS)
CODE = "482913"
WRONG_CODE = "000000"

type Scenario = Callable[[FakeIdentityTransactions, FakeClock], str]


@pytest.fixture
def verify_sign_in_code(
    transactions: FakeIdentityTransactions, clock: FakeClock
) -> VerifySignInCode:
    return VerifySignInCode(transactions=transactions, clock=clock, code_secret=CODE_SECRET)


def _seed_challenge(transactions: FakeIdentityTransactions, clock: FakeClock) -> AuthChallenge:
    challenge_id = uuid7()
    mac = code_mac(CODE_SECRET, challenge_id, CODE)
    challenge = AuthChallenge.issue(challenge_id, EMAIL, mac, clock.now())
    transactions.challenges.rows[challenge.id] = challenge
    return challenge


async def _fail(verify_sign_in_code: VerifySignInCode, code: str = WRONG_CODE) -> None:
    with pytest.raises(AuthenticationError):
        await verify_sign_in_code(ADDRESS, code)


async def test_the_first_sign_in_creates_the_account_with_its_workspace_and_a_session(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    challenge = _seed_challenge(transactions, clock)

    token = await verify_sign_in_code(ADDRESS, CODE)

    [account] = transactions.accounts.rows.values()
    [session] = transactions.sessions.rows.values()
    assert account.email == EMAIL
    assert account.created_at == clock.now()
    assert account.workspace_id != account.id
    assert session.account_id == account.id
    assert session.token_hash == hash_session_token(token)
    assert session.expires_at == clock.now() + SESSION_LIFETIME
    assert transactions.challenges.rows[challenge.id].consumed_at == clock.now()
    assert transactions.locked_emails == [EMAIL]


async def test_signing_in_to_an_existing_account_reuses_it(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    account = Account.register(EMAIL, clock.now())
    transactions.accounts.rows[account.id] = account
    _seed_challenge(transactions, clock)

    token = await verify_sign_in_code(ADDRESS, CODE)

    assert list(transactions.accounts.rows.values()) == [account]
    assert transactions.sessions.rows[hash_session_token(token)].account_id == account.id


async def test_every_sign_in_gets_its_own_token(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    _seed_challenge(transactions, clock)
    first = await verify_sign_in_code(ADDRESS, CODE)
    _seed_challenge(transactions, clock)
    second = await verify_sign_in_code(ADDRESS, CODE)

    assert first != second
    assert len(transactions.accounts.rows) == 1
    assert len(transactions.sessions.rows) == 2


async def test_the_address_is_normalized_before_use(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    _seed_challenge(transactions, clock)

    await verify_sign_in_code("  Ana@Example.COM ", CODE)

    assert transactions.locked_emails == [EMAIL]
    assert [account.email for account in transactions.accounts.rows.values()] == [EMAIL]


async def test_a_wrong_code_spends_an_attempt_and_signs_nobody_in(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    challenge = _seed_challenge(transactions, clock)

    await _fail(verify_sign_in_code)

    stored = transactions.challenges.rows[challenge.id]
    assert stored.attempts_left == MAX_VERIFICATION_ATTEMPTS - 1
    assert stored.consumed_at is None
    assert transactions.accounts.rows == {}
    assert transactions.sessions.rows == {}


async def test_the_right_code_still_works_after_a_wrong_one(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    _seed_challenge(transactions, clock)
    await _fail(verify_sign_in_code)

    await verify_sign_in_code(ADDRESS, CODE)

    assert len(transactions.sessions.rows) == 1


async def test_the_third_wrong_code_exhausts_the_challenge_so_the_right_code_then_fails(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    challenge = _seed_challenge(transactions, clock)
    for _ in range(MAX_VERIFICATION_ATTEMPTS):
        await _fail(verify_sign_in_code)

    await _fail(verify_sign_in_code, CODE)

    assert transactions.challenges.rows[challenge.id].attempts_left == 0
    assert transactions.sessions.rows == {}


async def test_a_consumed_challenge_cannot_be_used_again(
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    _seed_challenge(transactions, clock)
    await verify_sign_in_code(ADDRESS, CODE)

    await _fail(verify_sign_in_code, CODE)

    assert len(transactions.sessions.rows) == 1


def _no_challenge(_transactions: FakeIdentityTransactions, _clock: FakeClock) -> str:
    return CODE


def _wrong_code(transactions: FakeIdentityTransactions, clock: FakeClock) -> str:
    _seed_challenge(transactions, clock)
    return WRONG_CODE


def _expired(transactions: FakeIdentityTransactions, clock: FakeClock) -> str:
    _seed_challenge(transactions, clock)
    clock.advance(CHALLENGE_VALIDITY)
    return CODE


def _consumed(transactions: FakeIdentityTransactions, clock: FakeClock) -> str:
    challenge = _seed_challenge(transactions, clock)
    transactions.challenges.rows[challenge.id] = challenge.consume(clock.now())
    return CODE


@pytest.mark.parametrize("scenario", [_no_challenge, _wrong_code, _expired, _consumed])
async def test_every_failure_gives_the_same_generic_error(
    scenario: Scenario,
    verify_sign_in_code: VerifySignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    code = scenario(transactions, clock)

    with pytest.raises(AuthenticationError) as raised:
        await verify_sign_in_code(ADDRESS, code)

    assert type(raised.value) is AuthenticationError
    assert raised.value.message == SIGN_IN_FAILED_MESSAGE
    assert transactions.sessions.rows == {}
