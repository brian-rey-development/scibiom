from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid7

from scibiom_core.identity.domain.auth_challenge import CHALLENGE_VALIDITY, AuthChallenge
from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.domain.verification_code import code_mac, generate_code
from scibiom_core.identity.ports.email_sender import EmailMessage

if TYPE_CHECKING:
    from datetime import datetime

    from scibiom_core.identity.ports.challenges import ChallengeRepository
    from scibiom_core.identity.ports.email_sender import EmailSender
    from scibiom_core.identity.ports.transactions import IdentityTransactions
    from scibiom_core.kernel.clock import Clock

ISSUANCE_COOLDOWN = timedelta(seconds=60)
ISSUANCE_WINDOW = timedelta(hours=1)
MAX_ISSUANCES_PER_EMAIL = 5
CODE_VALIDITY_MINUTES = int(CHALLENGE_VALIDITY.total_seconds()) // 60

SIGN_IN_SUBJECT = "Your Scibiom sign-in code"
SIGN_IN_BODY = (
    "Your Scibiom sign-in code is {code}.\n\n"
    "It expires in {minutes} minutes.\n\n"
    "If you did not request this code, ignore this email.\n"
)


def _sign_in_message(email: Email, code: str) -> EmailMessage:
    body = SIGN_IN_BODY.format(code=code, minutes=CODE_VALIDITY_MINUTES)
    return EmailMessage(recipient=email, subject=SIGN_IN_SUBJECT, body=body)


async def _is_suppressed(challenges: ChallengeRepository, email: Email, now: datetime) -> bool:
    latest = await challenges.latest_issued_at(email)
    if latest is not None and now - latest < ISSUANCE_COOLDOWN:
        return True
    issued = await challenges.count_issued_since(email, now - ISSUANCE_WINDOW)
    return issued >= MAX_ISSUANCES_PER_EMAIL


@dataclass(frozen=True, slots=True)
class RequestSignInCode:
    transactions: IdentityTransactions
    email_sender: EmailSender
    clock: Clock
    code_secret: bytes

    async def __call__(self, email: str) -> None:
        address = Email(email)
        now = self.clock.now()
        code = generate_code()
        async with self.transactions.begin() as transaction:
            await transaction.lock_email(address)
            issued = await self._issue(transaction.challenges, address, code, now)
        if issued:
            await self.email_sender.send(_sign_in_message(address, code))

    async def _issue(
        self, challenges: ChallengeRepository, email: Email, code: str, now: datetime
    ) -> bool:
        if await _is_suppressed(challenges, email, now):
            return False
        await challenges.invalidate_active(email, now)
        challenge_id = uuid7()
        mac = code_mac(self.code_secret, challenge_id, code)
        await challenges.add(AuthChallenge.issue(challenge_id, email, mac, now))
        return True
