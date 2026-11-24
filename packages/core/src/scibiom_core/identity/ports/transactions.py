from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from scibiom_core.identity.domain.email import Email
    from scibiom_core.identity.ports.accounts import AccountRepository
    from scibiom_core.identity.ports.challenges import ChallengeRepository
    from scibiom_core.identity.ports.sessions import SessionRepository


class IdentityTransaction(Protocol):
    @property
    def accounts(self) -> AccountRepository: ...

    @property
    def challenges(self) -> ChallengeRepository: ...

    @property
    def sessions(self) -> SessionRepository: ...

    async def lock_email(self, email: Email) -> None:
        """Make other transactions that lock the same address wait until this one ends."""
        ...


class IdentityTransactions(Protocol):
    def begin(self) -> AbstractAsyncContextManager[IdentityTransaction]:
        """Open a transaction that commits on normal exit and rolls back on an exception."""
        ...
