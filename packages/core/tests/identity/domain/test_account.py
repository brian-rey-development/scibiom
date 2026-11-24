from datetime import UTC, datetime

from scibiom_core.identity.domain.account import Account
from scibiom_core.identity.domain.email import Email

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def test_registered_account_keeps_its_email_and_creation_time() -> None:
    email = Email("ana@example.com")

    account = Account.register(email, NOW)

    assert account.email == email
    assert account.created_at == NOW


def test_registered_account_gets_its_own_workspace() -> None:
    account = Account.register(Email("ana@example.com"), NOW)

    assert account.workspace_id != account.id
