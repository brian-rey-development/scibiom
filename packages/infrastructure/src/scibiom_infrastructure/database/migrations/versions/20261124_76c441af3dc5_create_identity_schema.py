"""create identity schema

Revision ID: 76c441af3dc5
Create Date: 2026-11-24 13:56:25.918879
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "76c441af3dc5"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "identity"
DIGEST_BYTES = 32
MAX_VERIFICATION_ATTEMPTS = 3
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute(sa.schema.CreateSchema(SCHEMA))
    op.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO scibiom_app")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scibiom_app"
    )
    _create_accounts()
    _create_sessions()
    _create_auth_challenges()


def _create_accounts() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("workspace_id", sa.Uuid, nullable=False, unique=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.CheckConstraint("email = lower(btrim(email))", name="accounts_email_normalized"),
        schema=SCHEMA,
    )


def _create_sessions() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("token_hash", sa.LargeBinary, nullable=False, unique=True),
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.Column("expires_at", TIMESTAMP, nullable=False),
        sa.ForeignKeyConstraint(["account_id"], [f"{SCHEMA}.accounts.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            f"octet_length(token_hash) = {DIGEST_BYTES}", name="sessions_token_hash_length"
        ),
        sa.CheckConstraint("expires_at > created_at", name="sessions_expires_after_created"),
        schema=SCHEMA,
    )
    op.create_index("ix_sessions_account_id", "sessions", ["account_id"], schema=SCHEMA)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], schema=SCHEMA)


def _create_auth_challenges() -> None:
    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("code_mac", sa.LargeBinary, nullable=False),
        sa.Column("attempts_left", sa.SmallInteger, nullable=False),
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.Column("expires_at", TIMESTAMP, nullable=False),
        sa.Column("consumed_at", TIMESTAMP),
        sa.Column("invalidated_at", TIMESTAMP),
        *_auth_challenge_checks(),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_auth_challenges_email_created_at",
        "auth_challenges",
        ["email", "created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_auth_challenges_one_active",
        "auth_challenges",
        ["email"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("consumed_at IS NULL AND invalidated_at IS NULL"),
    )
    op.create_index(
        "ix_auth_challenges_expires_at", "auth_challenges", ["expires_at"], schema=SCHEMA
    )


def _auth_challenge_checks() -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint("email = lower(btrim(email))", name="auth_challenges_email_normalized"),
        sa.CheckConstraint(
            f"octet_length(code_mac) = {DIGEST_BYTES}", name="auth_challenges_code_mac_length"
        ),
        sa.CheckConstraint(
            f"attempts_left BETWEEN 0 AND {MAX_VERIFICATION_ATTEMPTS}",
            name="auth_challenges_attempts_left_range",
        ),
        sa.CheckConstraint("expires_at > created_at", name="auth_challenges_expires_after_created"),
        sa.CheckConstraint(
            "consumed_at IS NULL OR invalidated_at IS NULL",
            name="auth_challenges_not_consumed_and_invalidated",
        ),
    ]


def downgrade() -> None:
    op.execute(sa.schema.DropSchema(SCHEMA, cascade=True))
