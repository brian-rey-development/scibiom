from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from scibiom_core.identity.domain.account import Account
    from scibiom_core.identity.domain.email import Email


class AccountRepository(Protocol):
    async def find_by_email(self, email: Email) -> Account | None: ...

    async def find_by_id(self, account_id: UUID) -> Account | None: ...

    async def add(self, account: Account) -> None: ...
