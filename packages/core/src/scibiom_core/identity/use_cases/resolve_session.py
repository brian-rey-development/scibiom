from dataclasses import dataclass
from typing import TYPE_CHECKING

from scibiom_core.identity.domain.session import hash_session_token
from scibiom_core.kernel.errors import AuthenticationError

if TYPE_CHECKING:
    from scibiom_core.identity.ports.transactions import IdentityTransactions
    from scibiom_core.kernel.access import Actor
    from scibiom_core.kernel.clock import Clock

INVALID_SESSION_MESSAGE = "The session is not valid"


@dataclass(frozen=True, slots=True)
class ResolveSession:
    transactions: IdentityTransactions
    clock: Clock

    async def __call__(self, token: str) -> Actor:
        async with self.transactions.begin() as transaction:
            found = await transaction.sessions.find_with_actor(hash_session_token(token))
        if found is None:
            raise AuthenticationError(INVALID_SESSION_MESSAGE)
        session, actor = found
        if session.is_expired(self.clock.now()):
            raise AuthenticationError(INVALID_SESSION_MESSAGE)
        return actor
