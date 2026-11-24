from typing import Annotated

from fastapi import Depends, Request

from scibiom_api.bootstrap.container import Container
from scibiom_api.bootstrap.settings import Environment
from scibiom_api.transport.session_cookie import read_session_cookie
from scibiom_core.identity.use_cases.request_sign_in_code import RequestSignInCode
from scibiom_core.identity.use_cases.resolve_session import (
    INVALID_SESSION_MESSAGE,
    ResolveSession,
)
from scibiom_core.identity.use_cases.verify_sign_in_code import VerifySignInCode
from scibiom_core.kernel.access import Actor
from scibiom_core.kernel.errors import AuthenticationError
from scibiom_core.kernel.readiness import ReadinessCheck


def _get_container(request: Request) -> Container:
    container: object = request.app.state.container
    if isinstance(container, Container):
        return container
    message = "container is not initialised"
    raise RuntimeError(message)


def _get_readiness_checks(
    container: Annotated[Container, Depends(_get_container)],
) -> tuple[ReadinessCheck, ...]:
    return container.readiness_checks


def _get_readiness_timeout(container: Annotated[Container, Depends(_get_container)]) -> float:
    return container.settings.readiness_timeout_seconds


def _get_environment(container: Annotated[Container, Depends(_get_container)]) -> Environment:
    return container.settings.environment


def _get_request_sign_in_code(
    container: Annotated[Container, Depends(_get_container)],
) -> RequestSignInCode:
    return container.request_sign_in_code


def _get_verify_sign_in_code(
    container: Annotated[Container, Depends(_get_container)],
) -> VerifySignInCode:
    return container.verify_sign_in_code


def _get_resolve_session(
    container: Annotated[Container, Depends(_get_container)],
) -> ResolveSession:
    return container.resolve_session


type ReadinessChecksDep = Annotated[tuple[ReadinessCheck, ...], Depends(_get_readiness_checks)]
type ReadinessTimeoutDep = Annotated[float, Depends(_get_readiness_timeout)]
type EnvironmentDep = Annotated[Environment, Depends(_get_environment)]
type RequestSignInCodeDep = Annotated[RequestSignInCode, Depends(_get_request_sign_in_code)]
type VerifySignInCodeDep = Annotated[VerifySignInCode, Depends(_get_verify_sign_in_code)]
type ResolveSessionDep = Annotated[ResolveSession, Depends(_get_resolve_session)]


async def _get_actor(
    request: Request, environment: EnvironmentDep, resolve_session: ResolveSessionDep
) -> Actor:
    token = read_session_cookie(request, environment)
    if token is None:
        raise AuthenticationError(INVALID_SESSION_MESSAGE)
    return await resolve_session(token)


type ActorDep = Annotated[Actor, Depends(_get_actor)]
