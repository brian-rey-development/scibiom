import re
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.auth_challenge import CHALLENGE_VALIDITY
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.verification_code import code_mac
from scibiom_core.identity.use_cases.request_sign_in_code import (
    ISSUANCE_COOLDOWN,
    ISSUANCE_WINDOW,
    MAX_ISSUANCES_PER_EMAIL,
    RequestSignInCode,
)
from scibiom_core.kernel.errors import RuleViolationError, UnavailableError

if TYPE_CHECKING:
    from conftest import FakeClock, FakeEmailSender, FakeIdentityTransactions

CODE_SECRET = b"c" * 32
ADDRESS = "ana@example.com"
EMAIL = Email(ADDRESS)
OTHER_ADDRESS = "ben@example.com"
CODE_PATTERN = re.compile(r"\b\d{6}\b")
MICROSECOND = timedelta(microseconds=1)


@pytest.fixture
def request_sign_in_code(
    transactions: FakeIdentityTransactions, email_sender: FakeEmailSender, clock: FakeClock
) -> RequestSignInCode:
    return RequestSignInCode(
        transactions=transactions,
        email_sender=email_sender,
        clock=clock,
        code_secret=CODE_SECRET,
    )


def _code_in(body: str) -> str:
    match = CODE_PATTERN.search(body)
    assert match is not None
    return match.group()


async def test_a_code_is_emailed_and_stored_only_as_a_mac_of_that_code(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    email_sender: FakeEmailSender,
    clock: FakeClock,
) -> None:
    await request_sign_in_code(ADDRESS)

    [message] = email_sender.sent
    [challenge] = transactions.challenges.rows.values()
    code = _code_in(message.body)
    assert message.recipient == EMAIL
    assert challenge.email == EMAIL
    assert challenge.code_mac == code_mac(CODE_SECRET, challenge.id, code)
    assert challenge.created_at == clock.now()
    assert challenge.expires_at == clock.now() + CHALLENGE_VALIDITY
    assert transactions.locked_emails == [EMAIL]


async def test_the_email_gives_the_code_its_five_minute_expiry_and_an_ignore_notice(
    request_sign_in_code: RequestSignInCode, email_sender: FakeEmailSender
) -> None:
    await request_sign_in_code(ADDRESS)

    [message] = email_sender.sent
    assert "expires in 5 minutes" in message.body
    assert "did not request this code, ignore this email" in message.body
    assert message.subject


async def test_the_address_is_normalized_before_use(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    email_sender: FakeEmailSender,
) -> None:
    await request_sign_in_code("  Ana@Example.COM ")

    assert email_sender.sent[0].recipient == EMAIL
    assert transactions.locked_emails == [EMAIL]


async def test_an_invalid_address_is_rejected_before_anything_is_stored_or_sent(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    email_sender: FakeEmailSender,
) -> None:
    with pytest.raises(RuleViolationError):
        await request_sign_in_code("not-an-address")

    assert transactions.challenges.rows == {}
    assert email_sender.sent == []


async def test_a_new_code_invalidates_the_earlier_active_one(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    clock: FakeClock,
) -> None:
    await request_sign_in_code(ADDRESS)
    [first_id] = transactions.challenges.rows
    clock.advance(ISSUANCE_COOLDOWN)

    await request_sign_in_code(ADDRESS)

    rows = transactions.challenges.rows
    active = [challenge for challenge in rows.values() if challenge.invalidated_at is None]
    assert rows[first_id].invalidated_at == clock.now()
    assert len(active) == 1
    assert active[0].id != first_id


async def test_a_request_inside_the_cooldown_is_suppressed_without_an_error(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    email_sender: FakeEmailSender,
    clock: FakeClock,
) -> None:
    await request_sign_in_code(ADDRESS)
    clock.advance(ISSUANCE_COOLDOWN - MICROSECOND)

    await request_sign_in_code(ADDRESS)

    assert len(email_sender.sent) == 1
    assert len(transactions.challenges.rows) == 1

    clock.advance(MICROSECOND)
    await request_sign_in_code(ADDRESS)

    assert len(email_sender.sent) == 2


async def test_the_hourly_limit_suppresses_requests_until_the_oldest_issuance_leaves_the_window(
    request_sign_in_code: RequestSignInCode, email_sender: FakeEmailSender, clock: FakeClock
) -> None:
    first_issuance = clock.now()
    for _ in range(MAX_ISSUANCES_PER_EMAIL):
        await request_sign_in_code(ADDRESS)
        clock.advance(ISSUANCE_COOLDOWN)

    clock.advance(first_issuance + ISSUANCE_WINDOW - clock.now())
    await request_sign_in_code(ADDRESS)

    assert len(email_sender.sent) == MAX_ISSUANCES_PER_EMAIL

    clock.advance(MICROSECOND)
    await request_sign_in_code(ADDRESS)

    assert len(email_sender.sent) == MAX_ISSUANCES_PER_EMAIL + 1


async def test_the_limits_of_one_address_do_not_affect_another(
    request_sign_in_code: RequestSignInCode, email_sender: FakeEmailSender
) -> None:
    await request_sign_in_code(ADDRESS)

    await request_sign_in_code(OTHER_ADDRESS)

    assert [message.recipient.value for message in email_sender.sent] == [ADDRESS, OTHER_ADDRESS]


async def test_a_delivery_failure_propagates_and_keeps_the_challenge_so_a_retry_is_suppressed(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    email_sender: FakeEmailSender,
) -> None:
    email_sender.failure = UnavailableError("send failed")
    with pytest.raises(UnavailableError):
        await request_sign_in_code(ADDRESS)

    assert len(transactions.challenges.rows) == 1

    email_sender.failure = None
    await request_sign_in_code(ADDRESS)

    assert email_sender.sent == []


async def test_a_known_and_an_unknown_address_get_the_same_challenge_and_email(
    request_sign_in_code: RequestSignInCode,
    transactions: FakeIdentityTransactions,
    email_sender: FakeEmailSender,
    clock: FakeClock,
) -> None:
    await transactions.accounts.add(Account.register(EMAIL, clock.now()))

    await request_sign_in_code(ADDRESS)
    await request_sign_in_code(OTHER_ADDRESS)

    known, unknown = email_sender.sent
    known_challenge, unknown_challenge = transactions.challenges.rows.values()
    assert known.subject == unknown.subject
    assert known.body.replace(_code_in(known.body), "") == unknown.body.replace(
        _code_in(unknown.body), ""
    )
    assert known_challenge.attempts_left == unknown_challenge.attempts_left
    assert known_challenge.expires_at == unknown_challenge.expires_at
