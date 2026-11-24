from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

DATABASE_CHECK_NAME = "database"


@dataclass(frozen=True, slots=True)
class DatabaseReadinessCheck:
    engine: AsyncEngine

    @property
    def name(self) -> str:
        return DATABASE_CHECK_NAME

    async def probe(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
