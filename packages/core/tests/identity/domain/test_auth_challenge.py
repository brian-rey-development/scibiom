from datetime import UTC, datetime, timedelta
from uuid import UUID

from scibiom_core.identity.domain.auth_challenge import (
    CHALLENGE_VALIDITY,
    MAX_VERIFICATION_ATTEMPTS,
    AuthChallenge,
)
from scibiom_core.identity.domain.email import Email

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
CHALLENGE_ID = UUID("0192f3a0-0000-7000-8000-000000000001")
CODE_MAC = b"\x01" * 32
EMAIL = Email("ana@example.com")


def _sign_in() -> AuthChallenge:
    return AuthChallenge.issue(CHALLENGE_ID, EMAIL, CODE_MAC, NOW)


def test_issued_challenge_is_usable_with_all_attempts_until_it_expires() -> None:
    challenge = _sign_in()

    assert challenge.attempts_left == MAX_VERIFICATION_ATTEMPTS
    assert challenge.expires_at == NOW + CHALLENGE_VALIDITY
    assert challenge.consumed_at is None
    assert challenge.invalidated_at is None
    assert challenge.is_usable(NOW)


def test_challenge_is_usable_until_the_instant_it_expires() -> None:
    challenge = _sign_in()
    last_valid_instant = challenge.expires_at - timedelta(microseconds=1)

    assert challenge.is_usable(last_valid_instant)
    assert not challenge.is_usable(challenge.expires_at)
    assert not challenge.is_usable(challenge.expires_at + timedelta(seconds=1))


def test_failed_attempts_use_up_the_attempts_without_changing_the_original() -> None:
    challenge = _sign_in()

    after_one = challenge.record_failed_attempt()

    assert after_one.attempts_left == MAX_VERIFICATION_ATTEMPTS - 1
    assert challenge.attempts_left == MAX_VERIFICATION_ATTEMPTS
    assert after_one.is_usable(NOW)


def test_challenge_is_not_usable_once_every_attempt_failed() -> None:
    challenge = _sign_in()

    for _ in range(MAX_VERIFICATION_ATTEMPTS):
        challenge = challenge.record_failed_attempt()

    assert challenge.attempts_left == 0
    assert not challenge.is_usable(NOW)


def test_consumed_challenge_is_not_usable() -> None:
    consumed = _sign_in().consume(NOW)

    assert consumed.consumed_at == NOW
    assert not consumed.is_usable(NOW)


def test_invalidated_challenge_is_not_usable() -> None:
    invalidated = _sign_in().invalidate(NOW)

    assert invalidated.invalidated_at == NOW
    assert not invalidated.is_usable(NOW)
