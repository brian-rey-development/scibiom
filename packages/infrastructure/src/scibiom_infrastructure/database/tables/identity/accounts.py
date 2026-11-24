from sqlalchemy import Column, DateTime, Table, Text, Uuid

from scibiom_infrastructure.database.tables.identity.metadata import identity_metadata

accounts = Table(
    "accounts",
    identity_metadata,
    Column("id", Uuid, primary_key=True),
    Column("workspace_id", Uuid, nullable=False, unique=True),
    Column("email", Text, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
