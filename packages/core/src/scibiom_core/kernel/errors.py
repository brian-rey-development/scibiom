from typing import ClassVar


class DomainError(Exception):
    """Base for expected business failures.

    `message` is shown to API clients, so it must never contain personal data.
    """

    code: ClassVar[str] = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RuleViolationError(DomainError):
    code = "rule_violation"


class AuthenticationError(DomainError):
    code = "authentication_failed"


class UnavailableError(DomainError):
    code = "unavailable"
