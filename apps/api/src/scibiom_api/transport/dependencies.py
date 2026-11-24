from typing import Annotated

from fastapi import Depends, Request

from scibiom_api.bootstrap.container import Container
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


type ReadinessChecksDep = Annotated[tuple[ReadinessCheck, ...], Depends(_get_readiness_checks)]
type ReadinessTimeoutDep = Annotated[float, Depends(_get_readiness_timeout)]
