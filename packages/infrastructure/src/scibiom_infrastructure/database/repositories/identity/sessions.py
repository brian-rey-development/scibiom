from dataclasses import asdict, dataclass, fields
from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select

from scibiom_core.identity.domain.session import Session
from scibiom_core.kernel.access import Actor
from scibiom_infrastructure.database.tables.identity.accounts import accounts
from scibiom_infrastructure.database.tables.identity.sessions import sessions

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

SESSION_FIELDS = tuple(field.name for field in fields(Session))


@dataclass(frozen=True, slots=True)
class SqlSessionRepository:
    connection: AsyncConnection

    async def add(self, session: Session) -> None:
        await self.connection.execute(insert(sessions).values(asdict(session)))

    async def find_with_actor(self, token_hash: bytes) -> tuple[Session, Actor] | None:
        statement = (
            select(sessions, accounts.c.workspace_id)
            .join(accounts, accounts.c.id == sessions.c.account_id)
            .where(sessions.c.token_hash == token_hash)
        )
        row = (await self.connection.execute(statement)).one_or_none()
        if row is None:
            return None
        session = Session(**{name: getattr(row, name) for name in SESSION_FIELDS})
        return session, Actor(session.account_id, row.workspace_id)

    async def delete_by_token_hash(self, token_hash: bytes) -> None:
        await self.connection.execute(delete(sessions).where(sessions.c.token_hash == token_hash))
