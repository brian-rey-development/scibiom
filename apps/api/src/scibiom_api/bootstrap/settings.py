from enum import StrEnum
from typing import Self
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from scibiom_infrastructure.database.settings import DatabaseSettings
from scibiom_infrastructure.observability.logging import LogLevel

ALLOWED_ORIGIN_SCHEMES = frozenset({"http", "https"})
HTTPS_SCHEME = "https"
SECURE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})
DEFAULT_READINESS_TIMEOUT_SECONDS = 2.0
MAX_READINESS_TIMEOUT_SECONDS = 10


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


DOCS_ENVIRONMENTS = frozenset({Environment.LOCAL, Environment.TEST})
HARDENED_ENVIRONMENTS = frozenset({Environment.STAGING, Environment.PRODUCTION})


def _validate_origin(origin: str) -> str:
    if "*" in origin:
        message = "CORS origins must be explicit, wildcards are not allowed"
        raise ValueError(message)
    parsed = urlsplit(origin)
    if parsed.scheme not in ALLOWED_ORIGIN_SCHEMES or not parsed.hostname:
        message = "CORS origins must have an http or https scheme and a host"
        raise ValueError(message)
    if parsed.path or parsed.query or parsed.fragment:
        message = "CORS origins must not contain a path, query or fragment"
        raise ValueError(message)
    return f"{parsed.scheme}://{parsed.netloc.lower()}"


def _enforces_tls(database_url: str) -> bool:
    # libpq honors the last sslmode when the parameter is repeated.
    modes = parse_qs(urlsplit(database_url).query).get("sslmode", [])
    return bool(modes) and modes[-1] in SECURE_SSL_MODES


class CorsSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed_origins: tuple[str, ...] = ()

    @field_validator("allowed_origins")
    @classmethod
    def _validate_allowed_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_validate_origin(origin) for origin in origins)


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIBIOM_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )

    environment: Environment
    log_level: LogLevel = "INFO"
    database: DatabaseSettings
    cors: CorsSettings = CorsSettings()
    readiness_timeout_seconds: float = Field(
        default=DEFAULT_READINESS_TIMEOUT_SECONDS,
        gt=0,
        le=MAX_READINESS_TIMEOUT_SECONDS,
    )

    @model_validator(mode="after")
    def _require_secure_transport_when_hardened(self) -> Self:
        if self.environment not in HARDENED_ENVIRONMENTS:
            return self
        if any(urlsplit(origin).scheme != HTTPS_SCHEME for origin in self.cors.allowed_origins):
            message = "CORS origins must use https outside local and test"
            raise ValueError(message)
        if not _enforces_tls(self.database.url.get_secret_value()):
            message = "database URL must set sslmode to require, verify-ca or verify-full"
            raise ValueError(message)
        return self

    @property
    def interactive_docs_enabled(self) -> bool:
        return self.environment in DOCS_ENVIRONMENTS


def load_settings() -> ApiSettings:
    # model_validate routes through BaseSettings.__init__, which reads the environment, and
    # avoids Pyright's missing-argument error on a bare ApiSettings().
    return ApiSettings.model_validate({})
