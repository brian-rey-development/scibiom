from typing import Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_TIMEOUT_SECONDS = 30


class EmailSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65_535)
    sender: str = Field(min_length=1)
    username: str | None = Field(default=None, min_length=1)
    password: SecretStr | None = Field(default=None, min_length=1)
    use_tls: bool = False
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, le=MAX_TIMEOUT_SECONDS)

    @model_validator(mode="after")
    def _require_both_credentials_or_neither(self) -> Self:
        if (self.username is None) != (self.password is None):
            message = "username and password must be set together"
            raise ValueError(message)
        return self
