from dataclasses import dataclass, replace
from datetime import timedelta
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from scibiom_core.identity.domain.email import Email

CHALLENGE_VALIDITY = timedelta(minutes=5)
MAX_VERIFICATION_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class AuthChallenge:
    id: UUID
    email: Email
    code_mac: bytes
    attempts_left: int
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None
    invalidated_at: datetime | None

    @classmethod
    def issue(cls, challenge_id: UUID, email: Email, code_mac: bytes, now: datetime) -> Self:
        return cls(
            id=challenge_id,
            email=email,
            code_mac=code_mac,
            attempts_left=MAX_VERIFICATION_ATTEMPTS,
            created_at=now,
            expires_at=now + CHALLENGE_VALIDITY,
            consumed_at=None,
            invalidated_at=None,
        )

    def is_usable(self, now: datetime) -> bool:
        return (
            self.consumed_at is None
            and self.invalidated_at is None
            and self.attempts_left > 0
            and now < self.expires_at
        )

    def record_failed_attempt(self) -> Self:
        return replace(self, attempts_left=self.attempts_left - 1)

    def consume(self, now: datetime) -> Self:
        return replace(self, consumed_at=now)

    def invalidate(self, now: datetime) -> Self:
        return replace(self, invalidated_at=now)
