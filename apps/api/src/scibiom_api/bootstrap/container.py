from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scibiom_api.bootstrap.settings import ApiSettings
from scibiom_infrastructure.database.engine import create_database_engine
from scibiom_infrastructure.database.readiness import DatabaseReadinessCheck

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from scibiom_core.kernel.readiness import ReadinessCheck


@dataclass(frozen=True, slots=True)
class Container:
    settings: ApiSettings
    engine: AsyncEngine
    readiness_checks: tuple[ReadinessCheck, ...]


type ContainerFactory = Callable[[ApiSettings], Container]


def build_container(settings: ApiSettings) -> Container:
    engine = create_database_engine(settings.database)
    return Container(
        settings=settings,
        engine=engine,
        readiness_checks=(DatabaseReadinessCheck(engine),),
    )


async def dispose_container(container: Container) -> None:
    await container.engine.dispose()
