import re
from dataclasses import dataclass

from scibiom_core.kernel.errors import RuleViolationError

MAX_EMAIL_LENGTH = 254
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+")
INVALID_EMAIL_MESSAGE = "Invalid email address"


def _is_valid(address: str) -> bool:
    return (
        len(address) <= MAX_EMAIL_LENGTH
        and address.isascii()
        and address.isprintable()
        and EMAIL_PATTERN.fullmatch(address) is not None
    )


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _is_valid(normalized):
            raise RuleViolationError(INVALID_EMAIL_MESSAGE)
        object.__setattr__(self, "value", normalized)
