import re
from dataclasses import dataclass, field, replace
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from scibiom_api.bootstrap.container import Container, build_container
from scibiom_api.bootstrap.settings import ApiSettings, Environment
from scibiom_api.main import create_app
from scibiom_core.identity.domain.session import SESSION_LIFETIME
from scibiom_core.identity.ports.email_sender import EmailMessage

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

pytestmark = pytest.mark.integration

SIX_DIGITS = re.compile(r"\d{6}")


@dataclass(slots=True)
class CapturingEmailSender:
    messages: list[EmailMessage] = field(default_factory=list[EmailMessage])

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def _container_factory(sender: CapturingEmailSender) -> Callable[[ApiSettings], Container]:
    def factory(settings: ApiSettings) -> Container:
        container = build_container(settings)
        request_sign_in_code = replace(container.request_sign_in_code, email_sender=sender)
        return replace(container, request_sign_in_code=request_sign_in_code)

    return factory


def _issued_code(sender: CapturingEmailSender) -> str:
    match = SIX_DIGITS.search(sender.messages[0].body)
    assert match is not None
    return match.group()


@pytest.fixture
def sender() -> CapturingEmailSender:
    return CapturingEmailSender()


@pytest.fixture
def sign_in_client(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
    sender: CapturingEmailSender,
    local_database_url: str,
) -> Iterator[TestClient]:
    settings = settings_factory(Environment.TEST, (), local_database_url)
    app = create_app(settings, _container_factory(sender))
    with TestClient(app) as client:
        yield client


def test_a_code_from_the_email_signs_in_once(
    sign_in_client: TestClient, sender: CapturingEmailSender
) -> None:
    email = f"{uuid4().hex}@example.com"

    requested = sign_in_client.post("/v1/auth/codes", json={"email": email})
    credentials = {"email": email, "code": _issued_code(sender)}
    signed_in = sign_in_client.post("/v1/auth/sessions", json=credentials)
    replayed = sign_in_client.post("/v1/auth/sessions", json=credentials)

    assert requested.status_code == HTTPStatus.ACCEPTED
    assert requested.content == b""
    assert signed_in.status_code == HTTPStatus.NO_CONTENT
    cookie = SimpleCookie(signed_in.headers["set-cookie"])["scibiom_session"]
    assert cookie.value
    assert cookie["httponly"]
    assert cookie["max-age"] == str(int(SESSION_LIFETIME.total_seconds()))
    assert cookie["samesite"].lower() == "strict"
    assert replayed.status_code == HTTPStatus.UNAUTHORIZED
    assert "set-cookie" not in replayed.headers
