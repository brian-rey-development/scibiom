from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from scibiom_core.identity.domain.auth_challenge import AuthChallenge
    from scibiom_core.identity.domain.email import Email


class ChallengeRepository(Protocol):
    """An active challenge is neither consumed nor invalidated, whatever its expiry or attempts.

    The database allows at most one active challenge per address.
    """

    async def add(self, challenge: AuthChallenge) -> None: ...

    async def lock_active(self, email: Email) -> AuthChallenge | None:
        """Read the active challenge and hold its row until the transaction ends."""
        ...

    async def save(self, challenge: AuthChallenge) -> None:
        """Persist the attempts, consumption and invalidation of an existing challenge."""
        ...

    async def invalidate_active(self, email: Email, now: datetime) -> None: ...

    async def count_issued_since(self, email: Email, since: datetime) -> int:
        """Count challenges issued to the address at or after `since`."""
        ...

    async def latest_issued_at(self, email: Email) -> datetime | None:
        """Return when a challenge was last issued to the address."""
        ...
