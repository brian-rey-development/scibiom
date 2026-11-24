from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from scibiom_core.identity.domain.session import Session
    from scibiom_core.kernel.access import Actor


class SessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def find_with_actor(self, token_hash: bytes) -> tuple[Session, Actor] | None:
        """Read the session joined with its account."""
        ...

    async def delete_by_token_hash(self, token_hash: bytes) -> None:
        """Delete the session, and do nothing when it does not exist."""
        ...
