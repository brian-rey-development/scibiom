from dataclasses import dataclass
from typing import TYPE_CHECKING, Self
from uuid import uuid7

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from scibiom_core.identity.domain.email import Email


@dataclass(frozen=True, slots=True)
class Account:
    id: UUID
    workspace_id: UUID
    email: Email
    created_at: datetime

    @classmethod
    def register(cls, email: Email, now: datetime) -> Self:
        return cls(id=uuid7(), workspace_id=uuid7(), email=email, created_at=now)
