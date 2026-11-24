from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import OperationalError

from scibiom_infrastructure.database.readiness import DATABASE_CHECK_NAME, DatabaseReadinessCheck

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def test_check_is_named_database(unreachable_engine: AsyncEngine) -> None:
    assert DatabaseReadinessCheck(unreachable_engine).name == DATABASE_CHECK_NAME


async def test_probe_raises_when_the_database_is_unreachable(
    unreachable_engine: AsyncEngine,
) -> None:
    with pytest.raises(OperationalError):
        await DatabaseReadinessCheck(unreachable_engine).probe()
