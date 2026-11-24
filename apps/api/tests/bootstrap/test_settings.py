import os
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr, ValidationError

from scibiom_api.bootstrap.settings import (
    HARDENED_ENVIRONMENTS,
    MIN_SECRET_LENGTH,
    ApiSettings,
    CorsSettings,
    Environment,
    IdentitySettings,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

DATABASE_URL = "postgresql+psycopg://user:pass@db.internal:5432/scibiom"
HTTPS_ORIGIN = "https://scibiom.example"
HTTP_ORIGIN = "http://localhost:3000"
HARDENED = sorted(HARDENED_ENVIRONMENTS)
DSN_CREDENTIAL = "hunter2-password"
ENV_PREFIX = "SCIBIOM_"
ORIGIN_ERROR = "CORS origins must"
IDENTITY_KEY = "identity-secret-0123456789-abcdefghijklmn"
SHORT_KEY = "k" * (MIN_SECRET_LENGTH - 1)
EMAIL_API_KEY = "email-password-0123456789"
SMTP_EMAIL = {
    "SCIBIOM_EMAIL__HOST": "127.0.0.1",
    "SCIBIOM_EMAIL__PORT": "1025",
    "SCIBIOM_EMAIL__SENDER": "no-reply@scibiom.test",
}
SECURE_EMAIL = {
    "SCIBIOM_EMAIL__HOST": "smtp.resend.com",
    "SCIBIOM_EMAIL__PORT": "465",
    "SCIBIOM_EMAIL__SENDER": "no-reply@scibiom.test",
    "SCIBIOM_EMAIL__USERNAME": "resend",
    "SCIBIOM_EMAIL__PASSWORD": EMAIL_API_KEY,
    "SCIBIOM_EMAIL__USE_TLS": "true",
}


@pytest.mark.parametrize("origin", ["*", "https://*.example.com"])
def test_wildcard_origins_are_rejected(origin: str) -> None:
    with pytest.raises(ValidationError, match="wildcards are not allowed"):
        CorsSettings(allowed_origins=(origin,))


@pytest.mark.parametrize(
    "origin",
    ["https://example.com/app", "https://example.com/", "https://example.com?x=1", "example.com"],
)
def test_origins_must_be_bare_scheme_and_host(origin: str) -> None:
    with pytest.raises(ValidationError, match=ORIGIN_ERROR):
        CorsSettings(allowed_origins=(origin,))


def test_origins_are_normalised_to_lowercase_scheme_and_host() -> None:
    cors = CorsSettings(allowed_origins=("HTTPS://App.Example.COM:8443",))

    assert cors.allowed_origins == ("https://app.example.com:8443",)


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://app.example.com:443", "https://app.example.com"),
        ("http://localhost:80", "http://localhost"),
    ],
)
def test_default_ports_are_dropped_to_match_the_browser_origin(origin: str, expected: str) -> None:
    assert CorsSettings(allowed_origins=(origin,)).allowed_origins == (expected,)


@pytest.mark.parametrize("environment", HARDENED)
def test_http_origins_are_rejected_in_hardened_environments(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
    environment: Environment,
) -> None:
    with pytest.raises(ValidationError, match="must use https"):
        settings_factory(environment, (HTTP_ORIGIN,), f"{DATABASE_URL}?sslmode=require")


def test_http_origins_are_allowed_locally(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
) -> None:
    local = settings_factory(Environment.LOCAL, (HTTP_ORIGIN,), DATABASE_URL)

    assert local.cors.allowed_origins == (HTTP_ORIGIN,)


@pytest.mark.parametrize("environment", HARDENED)
@pytest.mark.parametrize("query", ["", "?sslmode=disable", "?sslmode=prefer", "?sslmode=allow"])
def test_hardened_environments_reject_database_urls_without_enforced_tls(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
    environment: Environment,
    query: str,
) -> None:
    with pytest.raises(ValidationError, match="sslmode"):
        settings_factory(environment, (HTTPS_ORIGIN,), DATABASE_URL + query)


@pytest.mark.parametrize("environment", HARDENED)
@pytest.mark.parametrize("mode", ["require", "verify-ca", "verify-full"])
def test_hardened_environments_accept_enforced_tls(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
    environment: Environment,
    mode: str,
) -> None:
    settings = settings_factory(environment, (HTTPS_ORIGIN,), f"{DATABASE_URL}?sslmode={mode}")

    assert not settings.interactive_docs_enabled


def test_the_last_sslmode_wins_when_the_parameter_is_repeated(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
) -> None:
    url = f"{DATABASE_URL}?sslmode=require&sslmode=disable"

    with pytest.raises(ValidationError, match="sslmode"):
        settings_factory(Environment.PRODUCTION, (HTTPS_ORIGIN,), url)


def test_local_environment_does_not_require_tls(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
) -> None:
    settings_factory(Environment.LOCAL, (), DATABASE_URL)


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    for name in [name for name in os.environ if name.startswith(ENV_PREFIX)]:
        monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCIBIOM_ENVIRONMENT", "test")
    monkeypatch.setenv("SCIBIOM_DATABASE__URL", DATABASE_URL)
    for name, value in SMTP_EMAIL.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


@pytest.fixture
def hardened_environment(clean_environment: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    clean_environment.setenv("SCIBIOM_IDENTITY__SECRET", IDENTITY_KEY)
    clean_environment.setenv("SCIBIOM_DATABASE__URL", f"{DATABASE_URL}?sslmode=require")
    return clean_environment


def test_invalid_settings_never_echo_nested_input_values(
    clean_environment: pytest.MonkeyPatch,
) -> None:
    clean_environment.setenv("SCIBIOM_IDENTITY__SECRET", IDENTITY_KEY)
    clean_environment.setenv(
        "SCIBIOM_DATABASE__DSN", f"postgresql://user:{DSN_CREDENTIAL}@db/scibiom"
    )

    with pytest.raises(ValidationError, match=r"database\.dsn") as excinfo:
        ApiSettings.model_validate({})

    assert DSN_CREDENTIAL not in str(excinfo.value)


def test_the_identity_secret_is_loaded_from_the_environment(
    clean_environment: pytest.MonkeyPatch,
) -> None:
    clean_environment.setenv("SCIBIOM_IDENTITY__SECRET", IDENTITY_KEY)

    assert ApiSettings.model_validate({}).identity.secret.get_secret_value() == IDENTITY_KEY


def test_a_short_identity_secret_is_rejected_without_echoing_it() -> None:
    with pytest.raises(ValidationError, match=f"at least {MIN_SECRET_LENGTH}") as excinfo:
        IdentitySettings(secret=SecretStr(SHORT_KEY))

    assert SHORT_KEY not in str(excinfo.value)


@pytest.mark.parametrize("environment", HARDENED)
def test_hardened_environments_reject_email_without_tls_or_credentials(
    hardened_environment: pytest.MonkeyPatch,
    environment: Environment,
) -> None:
    hardened_environment.setenv("SCIBIOM_ENVIRONMENT", environment)

    with pytest.raises(ValidationError, match="email must use TLS and credentials"):
        ApiSettings.model_validate({})


@pytest.mark.parametrize("environment", HARDENED)
def test_hardened_environments_reject_email_with_credentials_but_no_tls(
    hardened_environment: pytest.MonkeyPatch,
    environment: Environment,
) -> None:
    hardened_environment.setenv("SCIBIOM_ENVIRONMENT", environment)
    hardened_environment.setenv("SCIBIOM_EMAIL__USERNAME", "resend")
    hardened_environment.setenv("SCIBIOM_EMAIL__PASSWORD", EMAIL_API_KEY)

    with pytest.raises(ValidationError, match="email must use TLS and credentials"):
        ApiSettings.model_validate({})


@pytest.mark.parametrize("environment", HARDENED)
def test_hardened_environments_accept_email_with_tls_and_credentials(
    hardened_environment: pytest.MonkeyPatch,
    environment: Environment,
) -> None:
    hardened_environment.setenv("SCIBIOM_ENVIRONMENT", environment)
    for name, value in SECURE_EMAIL.items():
        hardened_environment.setenv(name, value)

    settings = ApiSettings.model_validate({})

    assert settings.email.use_tls
    assert settings.email.password is not None
    assert settings.email.password.get_secret_value() == EMAIL_API_KEY
