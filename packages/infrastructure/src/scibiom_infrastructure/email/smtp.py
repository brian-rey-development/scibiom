import asyncio
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import TYPE_CHECKING

from scibiom_core.kernel.errors import UnavailableError

if TYPE_CHECKING:
    from scibiom_core.identity.ports.email_sender import EmailMessage
    from scibiom_infrastructure.email.settings import EmailSettings

DELIVERY_UNAVAILABLE_MESSAGE = "The email could not be sent, try again later"


@dataclass(frozen=True, slots=True)
class SmtpEmailSender:
    """SMTP delivery, with implicit TLS and login when the settings ask for them."""

    settings: EmailSettings

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._deliver, self._to_mime(message))

    def _to_mime(self, message: EmailMessage) -> MimeMessage:
        mime = MimeMessage()
        mime["From"] = self.settings.sender
        mime["To"] = message.recipient.value
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        return mime

    def _connect(self) -> smtplib.SMTP:
        settings = self.settings
        if settings.use_tls:
            return smtplib.SMTP_SSL(
                settings.host,
                settings.port,
                timeout=settings.timeout_seconds,
                context=ssl.create_default_context(),
            )
        return smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout_seconds)

    def _deliver(self, mime: MimeMessage) -> None:
        settings = self.settings
        try:
            connection = self._connect()
            try:
                if settings.username is not None and settings.password is not None:
                    connection.login(settings.username, settings.password.get_secret_value())
                connection.send_message(mime)
            finally:
                connection.close()
        except OSError, smtplib.SMTPException:
            raise UnavailableError(DELIVERY_UNAVAILABLE_MESSAGE) from None
