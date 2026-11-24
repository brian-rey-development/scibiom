import os
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from scibiom_api.bootstrap.settings import (
    HARDENED_ENVIRONMENTS,
    ApiSettings,
    CorsSettings,
    Environment,
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


def test_invalid_settings_never_echo_nested_input_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in [name for name in os.environ if name.startswith(ENV_PREFIX)]:
        monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCIBIOM_ENVIRONMENT", "test")
    monkeypatch.setenv("SCIBIOM_DATABASE__URL", DATABASE_URL)
    monkeypatch.setenv("SCIBIOM_DATABASE__DSN", f"postgresql://user:{DSN_CREDENTIAL}@db/scibiom")

    with pytest.raises(ValidationError, match=r"database\.dsn") as excinfo:
        ApiSettings.model_validate({})

    assert DSN_CREDENTIAL not in str(excinfo.value)
