from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, select

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email
from scibiom_infrastructure.database.tables.identity.accounts import accounts

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Row, Select
    from sqlalchemy.ext.asyncio import AsyncConnection


def _to_account(row: Row[Any]) -> Account:
    return Account(
        id=row.id,
        workspace_id=row.workspace_id,
        email=Email(row.email),
        created_at=row.created_at,
    )


@dataclass(frozen=True, slots=True)
class SqlAccountRepository:
    connection: AsyncConnection

    async def find_by_email(self, email: Email) -> Account | None:
        return await self._fetch(select(accounts).where(accounts.c.email == email.value))

    async def find_by_id(self, account_id: UUID) -> Account | None:
        return await self._fetch(select(accounts).where(accounts.c.id == account_id))

    async def add(self, account: Account) -> None:
        await self.connection.execute(
            insert(accounts).values(
                id=account.id,
                workspace_id=account.workspace_id,
                email=account.email.value,
                created_at=account.created_at,
            )
        )

    async def _fetch(self, statement: Select[Any]) -> Account | None:
        row = (await self.connection.execute(statement)).one_or_none()
        return None if row is None else _to_account(row)
