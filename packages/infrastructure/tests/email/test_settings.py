import pytest
from pydantic import SecretStr, ValidationError

from scibiom_infrastructure.email.settings import (
    EmailSettings,
)

API_KEY = "re_super-secret-key"
PLAIN = {"host": "127.0.0.1", "port": 1025, "sender": "auth@scibiom.test"}
SECURE = {
    "host": "smtp.resend.com",
    "port": 465,
    "sender": "auth@scibiom.test",
    "username": "resend",
    "password": API_KEY,
    "use_tls": True,
}


def test_plain_settings_need_no_credentials_and_default_to_no_tls() -> None:
    settings = EmailSettings.model_validate(PLAIN)

    assert (settings.username, settings.password, settings.use_tls) == (None, None, False)


def test_credentials_are_kept_as_a_secret() -> None:
    settings = EmailSettings.model_validate(SECURE)

    assert settings.password == SecretStr(API_KEY)
    assert settings.use_tls


@pytest.mark.parametrize(
    "invalid",
    [
        {k: v for k, v in PLAIN.items() if k != "host"},
        {**PLAIN, "port": 0},
        {**PLAIN, "port": 65_536},
        {**PLAIN, "sender": ""},
        {**PLAIN, "provider": "smtp"},
        {**PLAIN, "username": "resend"},
        {**PLAIN, "password": API_KEY},
        {**SECURE, "username": ""},
        {**SECURE, "password": ""},
    ],
)
def test_invalid_settings_are_rejected(invalid: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EmailSettings.model_validate(invalid)


@pytest.mark.parametrize("invalid", [{**PLAIN, "password": API_KEY}, {**SECURE, "port": 1_000_000}])
def test_the_password_never_appears_in_repr_or_validation_errors(
    invalid: dict[str, object],
) -> None:
    with pytest.raises(ValidationError) as error:
        EmailSettings.model_validate(invalid)

    assert API_KEY not in repr(EmailSettings.model_validate(SECURE))
    assert API_KEY not in str(error.value)
