from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from scibiom_core.identity.domain.email import Email


@dataclass(frozen=True, slots=True)
class EmailMessage:
    recipient: Email
    subject: str
    body: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None:
        """Deliver a plain-text message, raising `UnavailableError` when it could not be sent."""
        ...
