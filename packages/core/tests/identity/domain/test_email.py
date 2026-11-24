import pytest

from scibiom_core.identity.domain.email import MAX_EMAIL_LENGTH, Email
from scibiom_core.kernel.errors import RuleViolationError


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("ana@example.com", "ana@example.com"),
        ("  Ana@Example.COM \n", "ana@example.com"),
        ("ana+health@mail.example.co.uk", "ana+health@mail.example.co.uk"),
        ("a.n.a@gmail.com", "a.n.a@gmail.com"),
    ],
)
def test_email_is_trimmed_and_lowercased_without_provider_rules(raw: str, normalized: str) -> None:
    assert Email(raw).value == normalized


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "ana",
        "ana@",
        "@example.com",
        "ana@example",
        "ana@@example.com",
        "ana@example..com",
        "ana@.example.com",
        "ana@example.com.",
        "ana smith@example.com",
        "ana@exa mple.com",
        "ana@example.com\nbcc@example.com",
        "ana\x00@example.com",
        "añá@example.com",
        f"{'a' * MAX_EMAIL_LENGTH}@example.com",
    ],
)
def test_invalid_email_is_rejected(raw: str) -> None:
    with pytest.raises(RuleViolationError):
        Email(raw)


def test_rejection_does_not_echo_the_submitted_address() -> None:
    with pytest.raises(RuleViolationError) as error:
        Email("private-address")

    assert "private-address" not in error.value.message


def test_email_of_the_maximum_length_is_accepted() -> None:
    local_part = "a" * (MAX_EMAIL_LENGTH - len("@example.com"))

    assert Email(f"{local_part}@example.com").value.endswith("@example.com")
