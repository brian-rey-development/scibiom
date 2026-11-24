from sqlalchemy import Column, DateTime, ForeignKey, Index, LargeBinary, Table, Uuid

from scibiom_infrastructure.database.tables.identity.accounts import accounts
from scibiom_infrastructure.database.tables.identity.metadata import identity_metadata

sessions = Table(
    "sessions",
    identity_metadata,
    Column("id", Uuid, primary_key=True),
    Column("account_id", Uuid, ForeignKey(accounts.c.id, ondelete="CASCADE"), nullable=False),
    Column("token_hash", LargeBinary, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Index("ix_sessions_account_id", "account_id"),
    Index("ix_sessions_expires_at", "expires_at"),
)
