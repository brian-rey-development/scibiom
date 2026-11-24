import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from scibiom_core.identity.domain.session import (
    Session,
    hash_session_token,
    new_session_token,
)

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
ACCOUNT_ID = UUID("0192f3a0-0000-7000-8000-000000000001")
TOKEN_HASH = b"\x02" * 32


def test_a_started_session_lasts_fourteen_days() -> None:
    session = Session.start(ACCOUNT_ID, TOKEN_HASH, NOW)

    assert session.account_id == ACCOUNT_ID
    assert session.token_hash == TOKEN_HASH
    assert session.created_at == NOW
    assert session.expires_at == NOW + timedelta(days=14)


def test_session_is_valid_until_the_instant_it_expires() -> None:
    session = Session.start(ACCOUNT_ID, TOKEN_HASH, NOW)

    assert not session.is_expired(session.expires_at - timedelta(microseconds=1))
    assert session.is_expired(session.expires_at)
    assert session.is_expired(session.expires_at + timedelta(days=1))


def test_a_token_is_stored_as_its_sha256_digest() -> None:
    token = new_session_token()

    assert hash_session_token(token) == hashlib.sha256(token.encode()).digest()
