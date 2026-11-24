from typing import TYPE_CHECKING

import pytest

from scibiom_infrastructure.database.readiness import DatabaseReadinessCheck

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration


async def test_probe_succeeds_against_the_real_database(app_engine: AsyncEngine) -> None:
    assert await DatabaseReadinessCheck(app_engine).probe() is None
