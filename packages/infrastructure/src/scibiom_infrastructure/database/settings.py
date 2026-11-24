from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PSYCOPG_URL_PREFIX = "postgresql+psycopg://"

DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 5
DEFAULT_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_POOL_TIMEOUT_SECONDS = 5.0
DEFAULT_STATEMENT_TIMEOUT_MS = 15_000
DEFAULT_LOCK_TIMEOUT_MS = 5_000


def require_psycopg_url(url: SecretStr) -> SecretStr:
    if not url.get_secret_value().startswith(PSYCOPG_URL_PREFIX):
        message = f"database URL must start with {PSYCOPG_URL_PREFIX}"
        raise ValueError(message)
    return url


type PsycopgUrl = Annotated[SecretStr, AfterValidator(require_psycopg_url)]


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    url: PsycopgUrl
    pool_size: int = Field(default=DEFAULT_POOL_SIZE, ge=1, le=50)
    max_overflow: int = Field(default=DEFAULT_MAX_OVERFLOW, ge=0, le=50)
    connect_timeout_seconds: int = Field(default=DEFAULT_CONNECT_TIMEOUT_SECONDS, ge=1, le=60)
    pool_timeout_seconds: float = Field(default=DEFAULT_POOL_TIMEOUT_SECONDS, gt=0, le=30)
    statement_timeout_ms: int = Field(default=DEFAULT_STATEMENT_TIMEOUT_MS, ge=100, le=300_000)


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIBIOM_MIGRATION_",
        env_file=".env",
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )

    database_url: PsycopgUrl
    lock_timeout_ms: int = Field(default=DEFAULT_LOCK_TIMEOUT_MS, ge=100, le=60_000)
