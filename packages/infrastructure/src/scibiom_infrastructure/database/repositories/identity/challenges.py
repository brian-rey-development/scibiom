from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, insert, select, update

from scibiom_core.identity.domain.auth_challenge import AuthChallenge
from scibiom_core.identity.domain.email import Email
from scibiom_infrastructure.database.tables.identity.auth_challenges import auth_challenges

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import Row
    from sqlalchemy.ext.asyncio import AsyncConnection

ACTIVE = (auth_challenges.c.consumed_at.is_(None), auth_challenges.c.invalidated_at.is_(None))


def _to_challenge(row: Row[Any]) -> AuthChallenge:
    return AuthChallenge(
        id=row.id,
        email=Email(row.email),
        code_mac=row.code_mac,
        attempts_left=row.attempts_left,
        created_at=row.created_at,
        expires_at=row.expires_at,
        consumed_at=row.consumed_at,
        invalidated_at=row.invalidated_at,
    )


@dataclass(frozen=True, slots=True)
class SqlChallengeRepository:
    connection: AsyncConnection

    async def add(self, challenge: AuthChallenge) -> None:
        values = {**asdict(challenge), "email": challenge.email.value}
        await self.connection.execute(insert(auth_challenges).values(values))

    async def lock_active(self, email: Email) -> AuthChallenge | None:
        statement = (
            select(auth_challenges)
            .where(auth_challenges.c.email == email.value, *ACTIVE)
            .with_for_update()
        )
        row = (await self.connection.execute(statement)).one_or_none()
        return None if row is None else _to_challenge(row)

    async def save(self, challenge: AuthChallenge) -> None:
        await self.connection.execute(
            update(auth_challenges)
            .where(auth_challenges.c.id == challenge.id)
            .values(
                attempts_left=challenge.attempts_left,
                consumed_at=challenge.consumed_at,
                invalidated_at=challenge.invalidated_at,
            )
        )

    async def invalidate_active(self, email: Email, now: datetime) -> None:
        await self.connection.execute(
            update(auth_challenges)
            .where(auth_challenges.c.email == email.value, *ACTIVE)
            .values(invalidated_at=now)
        )

    async def count_issued_since(self, email: Email, since: datetime) -> int:
        statement = select(func.count()).where(
            auth_challenges.c.email == email.value, auth_challenges.c.created_at >= since
        )
        return (await self.connection.execute(statement)).scalar_one()

    async def latest_issued_at(self, email: Email) -> datetime | None:
        statement = select(func.max(auth_challenges.c.created_at)).where(
            auth_challenges.c.email == email.value
        )
        return (await self.connection.execute(statement)).scalar_one()
