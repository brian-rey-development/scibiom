from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING

from scibiom_api.bootstrap.container import ContainerFactory, dispose_container

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from fastapi import FastAPI

    from scibiom_api.bootstrap.settings import ApiSettings


def build_lifespan(
    settings: ApiSettings,
    container_factory: ContainerFactory,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        container = container_factory(settings)
        app.state.container = container
        try:
            yield
        finally:
            await dispose_container(container)

    return lifespan
