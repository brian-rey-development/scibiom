from sqlalchemy import Column, DateTime, Index, LargeBinary, SmallInteger, Table, Text, Uuid, text

from scibiom_infrastructure.database.tables.identity.metadata import identity_metadata

auth_challenges = Table(
    "auth_challenges",
    identity_metadata,
    Column("id", Uuid, primary_key=True),
    Column("email", Text, nullable=False),
    Column("code_mac", LargeBinary, nullable=False),
    Column("attempts_left", SmallInteger, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("consumed_at", DateTime(timezone=True)),
    Column("invalidated_at", DateTime(timezone=True)),
    Index("ix_auth_challenges_email_created_at", "email", "created_at"),
    Index(
        "uq_auth_challenges_one_active",
        "email",
        unique=True,
        postgresql_where=text("consumed_at IS NULL AND invalidated_at IS NULL"),
    ),
    Index("ix_auth_challenges_expires_at", "expires_at"),
)
