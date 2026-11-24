import smtplib
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.ports.email_sender import EmailMessage
from scibiom_core.kernel.errors import UnavailableError
from scibiom_infrastructure.email.settings import EmailSettings
from scibiom_infrastructure.email.smtp import SmtpEmailSender

if TYPE_CHECKING:
    from collections.abc import Callable
    from email.message import EmailMessage as MimeMessage

API_KEY = "re_super-secret-key"
SETTINGS = EmailSettings.model_validate(
    {"host": "127.0.0.1", "port": 1025, "sender": "auth@scibiom.test"}
)
SECURE_SETTINGS = SETTINGS.model_copy(
    update={"use_tls": True, "username": "resend", "password": SecretStr(API_KEY)}
)
MESSAGE = EmailMessage(Email("reader@example.com"), "Your code", "Your code is 123456")
UNUSED_PORT = 1


class FakeConnection:
    def __init__(
        self, send_error: Exception | None = None, login_error: Exception | None = None
    ) -> None:
        self.send_error = send_error
        self.login_error = login_error
        self.sent: list[MimeMessage] = []
        self.logins: list[tuple[str, str]] = []
        self.closed = False

    def login(self, username: str, password: str) -> None:
        if self.login_error:
            raise self.login_error
        self.logins.append((username, password))

    def close(self) -> None:
        self.closed = True

    def send_message(self, mime: MimeMessage) -> None:
        if self.send_error:
            raise self.send_error
        self.sent.append(mime)


def _connect_with(
    monkeypatch: pytest.MonkeyPatch,
    connection: FakeConnection | None = None,
    connect_error: Exception | None = None,
) -> list[str]:
    opened: list[str] = []

    def opener(name: str) -> Callable[..., FakeConnection]:
        def connect(*_args: object, **_kwargs: object) -> FakeConnection:
            opened.append(name)
            if connect_error:
                raise connect_error
            assert connection
            return connection

        return connect

    monkeypatch.setattr(smtplib, "SMTP", opener("SMTP"))
    monkeypatch.setattr(smtplib, "SMTP_SSL", opener("SMTP_SSL"))
    return opened


async def test_a_message_is_sent_with_the_configured_sender_and_the_connection_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    _connect_with(monkeypatch, connection)

    await SmtpEmailSender(SETTINGS).send(MESSAGE)

    (mime,) = connection.sent
    assert connection.closed
    assert (mime["From"], mime["To"], mime["Subject"]) == (
        "auth@scibiom.test",
        "reader@example.com",
        "Your code",
    )
    assert mime.get_content().strip() == "Your code is 123456"


async def test_plain_settings_open_a_plain_connection_without_logging_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    opened = _connect_with(monkeypatch, connection)

    await SmtpEmailSender(SETTINGS).send(MESSAGE)

    assert opened == ["SMTP"]
    assert connection.logins == []


async def test_tls_settings_open_an_implicit_tls_connection_and_log_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    opened = _connect_with(monkeypatch, connection)

    await SmtpEmailSender(SECURE_SETTINGS).send(MESSAGE)

    assert opened == ["SMTP_SSL"]
    assert connection.logins == [("resend", API_KEY)]


@pytest.mark.parametrize(
    "error", [smtplib.SMTPAuthenticationError(535, "no"), smtplib.SMTPServerDisconnected()]
)
async def test_a_login_failure_is_unavailable_and_closes_the_connection(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    connection = FakeConnection(login_error=error)
    _connect_with(monkeypatch, connection)

    with pytest.raises(UnavailableError):
        await SmtpEmailSender(SECURE_SETTINGS).send(MESSAGE)

    assert connection.closed
    assert connection.sent == []


@pytest.mark.parametrize(
    "error",
    [ConnectionRefusedError(), TimeoutError(), smtplib.SMTPConnectError(421, "busy")],
)
async def test_a_connection_failure_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    _connect_with(monkeypatch, connect_error=error)

    with pytest.raises(UnavailableError):
        await SmtpEmailSender(SETTINGS).send(MESSAGE)


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPRecipientsRefused({}),
        smtplib.SMTPDataError(554, "no"),
        TimeoutError(),
        smtplib.SMTPServerDisconnected(),
    ],
)
async def test_a_send_failure_is_unavailable_and_closes_the_connection(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    connection = FakeConnection(error)
    _connect_with(monkeypatch, connection)

    with pytest.raises(UnavailableError):
        await SmtpEmailSender(SETTINGS).send(MESSAGE)

    assert connection.closed


async def test_a_refused_connection_is_unavailable() -> None:
    settings = SETTINGS.model_copy(update={"port": UNUSED_PORT})

    with pytest.raises(UnavailableError):
        await SmtpEmailSender(settings).send(MESSAGE)
