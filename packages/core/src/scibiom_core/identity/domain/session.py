import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Self
from uuid import uuid7

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

SESSION_LIFETIME = timedelta(days=14)
SESSION_TOKEN_BYTES = 32


def new_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


@dataclass(frozen=True, slots=True)
class Session:
    id: UUID
    account_id: UUID
    token_hash: bytes
    created_at: datetime
    expires_at: datetime

    @classmethod
    def start(cls, account_id: UUID, token_hash: bytes, now: datetime) -> Self:
        return cls(
            id=uuid7(),
            account_id=account_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + SESSION_LIFETIME,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
