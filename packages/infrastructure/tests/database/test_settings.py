import pytest
from pydantic import SecretStr, ValidationError

from scibiom_infrastructure.database.settings import (
    PSYCOPG_URL_PREFIX,
    DatabaseSettings,
    MigrationSettings,
)

VALID_URL = f"{PSYCOPG_URL_PREFIX}user:pw@localhost:5432/db"
CREDENTIAL = "hunter2-password"
BAD_URL_WITH_CREDENTIAL = f"mysql://user:{CREDENTIAL}@localhost/db"
MIGRATION_URL_ENV = "SCIBIOM_MIGRATION_DATABASE_URL"
MIGRATION_LOCK_TIMEOUT_ENV = "SCIBIOM_MIGRATION_LOCK_TIMEOUT_MS"

DATABASE_FIELD_BOUNDS = {
    "pool_size": (1, 50),
    "max_overflow": (0, 50),
    "connect_timeout_seconds": (1, 60),
    "pool_timeout_seconds": (0.001, 30),
    "statement_timeout_ms": (100, 300_000),
}
MIGRATION_LOCK_TIMEOUT_BOUNDS = (100, 60_000)


def _outside_bounds() -> list[tuple[str, float]]:
    return [
        (field, value)
        for field, (lowest, highest) in DATABASE_FIELD_BOUNDS.items()
        for value in (lowest - 1, highest + 1)
    ]


def _at_bounds() -> list[tuple[str, float]]:
    return [(field, value) for field, bounds in DATABASE_FIELD_BOUNDS.items() for value in bounds]


@pytest.mark.parametrize(("field", "value"), _outside_bounds())
def test_value_outside_its_bounds_is_rejected(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings.model_validate({"url": VALID_URL, field: value})


@pytest.mark.parametrize(("field", "value"), _at_bounds())
def test_value_at_its_bounds_is_accepted(field: str, value: float) -> None:
    settings = DatabaseSettings.model_validate({"url": VALID_URL, field: value})

    assert getattr(settings, field) == value


@pytest.mark.parametrize(
    "value", [MIGRATION_LOCK_TIMEOUT_BOUNDS[0] - 1, MIGRATION_LOCK_TIMEOUT_BOUNDS[1] + 1]
)
def test_migration_lock_timeout_outside_its_bounds_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: int
) -> None:
    monkeypatch.setenv(MIGRATION_URL_ENV, VALID_URL)
    monkeypatch.setenv(MIGRATION_LOCK_TIMEOUT_ENV, str(value))

    with pytest.raises(ValidationError):
        MigrationSettings.model_validate({})


def test_settings_are_frozen() -> None:
    settings = DatabaseSettings(url=SecretStr(VALID_URL))

    with pytest.raises(ValidationError):
        settings.pool_size = 10


@pytest.mark.parametrize("url", [SecretStr(BAD_URL_WITH_CREDENTIAL), BAD_URL_WITH_CREDENTIAL])
def test_non_psycopg_database_url_is_rejected_without_leaking_the_password(
    url: SecretStr | str,
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        DatabaseSettings.model_validate({"url": url})

    assert PSYCOPG_URL_PREFIX in str(excinfo.value)
    assert CREDENTIAL not in str(excinfo.value)


def test_migration_settings_read_the_prefixed_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MIGRATION_URL_ENV, VALID_URL)

    settings = MigrationSettings.model_validate({})

    assert settings.database_url.get_secret_value() == VALID_URL


def test_migration_settings_reject_non_psycopg_url_without_leaking_the_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MIGRATION_URL_ENV, BAD_URL_WITH_CREDENTIAL)

    with pytest.raises(ValidationError) as excinfo:
        MigrationSettings.model_validate({})

    assert PSYCOPG_URL_PREFIX in str(excinfo.value)
    assert CREDENTIAL not in str(excinfo.value)
