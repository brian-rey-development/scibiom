from contextlib import ExitStack
from dataclasses import dataclass, replace
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid7

import pytest
from fastapi.testclient import TestClient

from scibiom_api.bootstrap.container import build_container
from scibiom_api.main import create_app
from scibiom_api.transport.dependencies import ActorDep  # noqa: TC001 - FastAPI resolves it at runtime
from scibiom_core.identity.use_cases.resolve_session import INVALID_SESSION_MESSAGE
from scibiom_core.kernel.access import Actor
from scibiom_core.kernel.errors import AuthenticationError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fastapi import FastAPI

    from scibiom_api.bootstrap.container import Container
    from scibiom_api.bootstrap.settings import ApiSettings

PROBLEM_MEDIA_TYPE = "application/problem+json"
type Outcome = Actor | AuthenticationError
type ClientResolving = Callable[[Outcome], tuple[TestClient, StubResolveSession]]

COOKIE_NAME = "scibiom_session"
SESSION_VALUE = "opaque-session-token"
SESSION_HEADER = {"cookie": f"{COOKIE_NAME}={SESSION_VALUE}"}
ACTOR = Actor(account_id=uuid7(), workspace_id=uuid7())


@dataclass(slots=True)
class StubResolveSession:
    outcome: Outcome
    tokens: list[str]

    async def __call__(self, token: str) -> Actor:
        self.tokens.append(token)
        if isinstance(self.outcome, AuthenticationError):
            raise self.outcome
        return self.outcome


def _add_whoami(app: FastAPI) -> None:
    @app.get("/whoami")
    async def whoami(actor: ActorDep) -> dict[str, str]:
        return {"account_id": str(actor.account_id), "workspace_id": str(actor.workspace_id)}


@pytest.fixture
def client_resolving(settings: ApiSettings) -> Iterator[ClientResolving]:
    with ExitStack() as stack:

        def open_client(outcome: Outcome) -> tuple[TestClient, StubResolveSession]:
            stub = StubResolveSession(outcome, [])

            def factory(active: ApiSettings) -> Container:
                return replace(build_container(active), resolve_session=stub)

            app = create_app(settings, factory)
            _add_whoami(app)
            return stack.enter_context(TestClient(app)), stub

        yield open_client


def test_a_request_without_the_cookie_is_rejected_without_resolving(
    client_resolving: ClientResolving,
) -> None:
    client, stub = client_resolving(ACTOR)

    response = client.get("/whoami")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json()["code"] == "authentication_failed"
    assert response.json()["detail"] == INVALID_SESSION_MESSAGE
    assert stub.tokens == []


def test_a_resolved_session_reaches_the_handler_as_an_actor_without_a_cookie(
    client_resolving: ClientResolving,
) -> None:
    client, stub = client_resolving(ACTOR)

    response = client.get("/whoami", headers=SESSION_HEADER)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "account_id": str(ACTOR.account_id),
        "workspace_id": str(ACTOR.workspace_id),
    }
    assert stub.tokens == [SESSION_VALUE]
    assert "set-cookie" not in response.headers


def test_a_rejected_session_is_unauthorized_and_sets_no_cookie(
    client_resolving: ClientResolving,
) -> None:
    client, _ = client_resolving(AuthenticationError(INVALID_SESSION_MESSAGE))

    response = client.get("/whoami", headers=SESSION_HEADER)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "authentication_failed"
    assert "set-cookie" not in response.headers
