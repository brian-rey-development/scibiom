import logging
from contextlib import ExitStack
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, override

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from scibiom_api.bootstrap.container import Container, ContainerFactory, build_container
from scibiom_api.bootstrap.settings import (
    ApiSettings,
    CorsSettings,
    Environment,
    IdentitySettings,
)
from scibiom_api.main import create_app
from scibiom_infrastructure.database.settings import DatabaseSettings
from scibiom_infrastructure.email.settings import EmailSettings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from fastapi import FastAPI
    from pydantic_settings import PydanticBaseSettingsSource

    from scibiom_core.kernel.readiness import ReadinessCheck

UVICORN_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")
UNREACHABLE_DATABASE_URL = "postgresql+psycopg://user:pass@127.0.0.1:1/unused"
IDENTITY_KEY = "test-identity-secret-0123456789-abcdefghij"
EMAIL_HOST = "smtp.scibiom.test"
EMAIL_PORT = 465
EMAIL_USERNAME = "resend"
EMAIL_API_KEY = "test-email-password"
EMAIL_SENDER = "no-reply@scibiom.test"


@dataclass(frozen=True, slots=True)
class PassingCheck:
    name: str = "passing"

    async def probe(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class FailingCheck:
    name: str = "failing"

    async def probe(self) -> None:
        message = "probe failed"
        raise ConnectionError(message)


class _LocalDatabase(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIBIOM_", env_file=".env", env_nested_delimiter="__", extra="ignore"
    )

    database: DatabaseSettings


class IsolatedApiSettings(ApiSettings):
    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def make_container_factory(checks: Sequence[ReadinessCheck]) -> ContainerFactory:
    def factory(settings: ApiSettings) -> Container:
        return replace(build_container(settings), readiness_checks=tuple(checks))

    return factory


@pytest.fixture(autouse=True)
def restored_logging() -> Iterator[None]:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    uvicorn_loggers = [logging.getLogger(name) for name in UVICORN_LOGGER_NAMES]
    saved_uvicorn = [
        (list(item.handlers), item.propagate, item.disabled) for item in uvicorn_loggers
    ]
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    for item, (handlers, propagate, disabled) in zip(uvicorn_loggers, saved_uvicorn, strict=True):
        item.handlers[:] = handlers
        item.propagate = propagate
        item.disabled = disabled


@pytest.fixture
def settings_factory() -> Callable[[Environment, tuple[str, ...], str], ApiSettings]:
    def build(environment: Environment, origins: tuple[str, ...], database_url: str) -> ApiSettings:
        return IsolatedApiSettings(
            environment=environment,
            database=DatabaseSettings(url=SecretStr(database_url)),
            cors=CorsSettings(allowed_origins=origins),
            identity=IdentitySettings(secret=SecretStr(IDENTITY_KEY)),
            email=EmailSettings(
                host=EMAIL_HOST,
                port=EMAIL_PORT,
                sender=EMAIL_SENDER,
                username=EMAIL_USERNAME,
                password=SecretStr(EMAIL_API_KEY),
                use_tls=True,
            ),
        )

    return build


@pytest.fixture
def settings(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
) -> ApiSettings:
    return settings_factory(Environment.TEST, (), UNREACHABLE_DATABASE_URL)


def _open_client(
    stack: ExitStack,
    settings: ApiSettings,
    checks: Sequence[ReadinessCheck],
    configure: Callable[[FastAPI], None] | None,
) -> TestClient:
    app = create_app(settings, make_container_factory(checks))
    if configure is not None:
        configure(app)
    return stack.enter_context(TestClient(app))


@pytest.fixture
def passing_check() -> ReadinessCheck:
    return PassingCheck()


@pytest.fixture
def failing_check() -> ReadinessCheck:
    return FailingCheck()


@pytest.fixture
def client_for_checks(
    settings: ApiSettings,
) -> Iterator[Callable[[Sequence[ReadinessCheck]], TestClient]]:
    with ExitStack() as stack:
        yield lambda checks: _open_client(stack, settings, checks, None)


@pytest.fixture
def client_with_routes(
    settings: ApiSettings,
    passing_check: ReadinessCheck,
) -> Iterator[Callable[[Callable[[FastAPI], None]], TestClient]]:
    with ExitStack() as stack:
        yield lambda configure: _open_client(stack, settings, (passing_check,), configure)


@pytest.fixture
def client(
    client_for_checks: Callable[[Sequence[ReadinessCheck]], TestClient],
    passing_check: ReadinessCheck,
) -> TestClient:
    return client_for_checks((passing_check,))


@pytest.fixture
def local_database_url() -> str:
    """The compose Postgres URL for the application role, read without the rest of `.env`."""
    return _LocalDatabase.model_validate({}).database.url.get_secret_value()
