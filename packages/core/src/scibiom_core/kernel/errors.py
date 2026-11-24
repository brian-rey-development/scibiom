from typing import ClassVar


class DomainError(Exception):
    """Base for expected business failures.

    `message` is shown to API clients, so it must never contain personal data.
    """

    code: ClassVar[str] = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class RuleViolationError(DomainError):
    code = "rule_violation"
