import hmac
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.session import Session, hash_session_token, new_session_token
from scibiom_core.identity.domain.verification_code import code_mac
from scibiom_core.kernel.errors import AuthenticationError

if TYPE_CHECKING:
    from datetime import datetime

    from scibiom_core.identity.domain.auth_challenge import AuthChallenge
    from scibiom_core.identity.ports.accounts import AccountRepository
    from scibiom_core.identity.ports.transactions import IdentityTransaction, IdentityTransactions
    from scibiom_core.kernel.clock import Clock

SIGN_IN_FAILED_MESSAGE = "The sign-in code is not valid"


async def _account_for(accounts: AccountRepository, email: Email, now: datetime) -> Account:
    existing = await accounts.find_by_email(email)
    if existing is not None:
        return existing
    account = Account.register(email, now)
    await accounts.add(account)
    return account


@dataclass(frozen=True, slots=True)
class VerifySignInCode:
    transactions: IdentityTransactions
    clock: Clock
    code_secret: bytes

    async def __call__(self, email: str, code: str) -> str:
        address = Email(email)
        now = self.clock.now()
        async with self.transactions.begin() as transaction:
            await transaction.lock_email(address)
            token = await self._verify(transaction, address, code, now)
        if token is None:
            raise AuthenticationError(SIGN_IN_FAILED_MESSAGE)
        return token

    async def _verify(
        self, transaction: IdentityTransaction, email: Email, code: str, now: datetime
    ) -> str | None:
        challenge = await transaction.challenges.lock_active(email)
        if challenge is None or not challenge.is_usable(now):
            return None
        if not self._code_matches(challenge, code):
            await transaction.challenges.save(challenge.record_failed_attempt())
            return None
        return await self._sign_in(transaction, email, challenge, now)

    def _code_matches(self, challenge: AuthChallenge, code: str) -> bool:
        expected = code_mac(self.code_secret, challenge.id, code)
        return hmac.compare_digest(challenge.code_mac, expected)

    async def _sign_in(
        self,
        transaction: IdentityTransaction,
        email: Email,
        challenge: AuthChallenge,
        now: datetime,
    ) -> str:
        await transaction.challenges.save(challenge.consume(now))
        account = await _account_for(transaction.accounts, email, now)
        token = new_session_token()
        await transaction.sessions.add(Session.start(account.id, hash_session_token(token), now))
        return token
