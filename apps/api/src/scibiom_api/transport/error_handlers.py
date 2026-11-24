from http import HTTPStatus
from types import MappingProxyType
from typing import TYPE_CHECKING

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from scibiom_api.transport.problems import FieldError, known_status, problem_response
from scibiom_core.kernel.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    RuleViolationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    from pydantic_core import ErrorDetails

DOMAIN_ERROR_STATUS: Mapping[type[DomainError], int] = MappingProxyType(
    {
        NotFoundError: HTTPStatus.NOT_FOUND,
        ConflictError: HTTPStatus.CONFLICT,
        RuleViolationError: HTTPStatus.UNPROCESSABLE_CONTENT,
    }
)
FALLBACK_DOMAIN_ERROR_STATUS = HTTPStatus.BAD_REQUEST
VALIDATION_FAILED_CODE = "validation_failed"
VALIDATION_FAILED_DETAIL = "Request validation failed"
UNKNOWN_HTTP_ERROR_CODE = "http_error"
FALLBACK_FIELD_MESSAGE = "Invalid value"
FIELD_ERROR_MESSAGES: Mapping[str, str] = MappingProxyType(
    {
        "missing": "Field required",
        "extra_forbidden": "Unexpected field",
        "json_invalid": "Invalid JSON",
        "model_attributes_type": "Invalid object",
        "int_parsing": "Must be an integer",
        "int_type": "Must be an integer",
        "float_parsing": "Must be a number",
        "float_type": "Must be a number",
        "bool_parsing": "Must be a boolean",
        "bool_type": "Must be a boolean",
        "string_type": "Must be a string",
        "uuid_parsing": "Must be a valid UUID",
        "uuid_type": "Must be a valid UUID",
        "date_parsing": "Must be a valid date",
        "datetime_parsing": "Must be a valid date and time",
        "enum": "Not an allowed value",
        "literal_error": "Not an allowed value",
        "string_too_short": "Too short",
        "string_too_long": "Too long",
        "string_pattern_mismatch": "Does not match the required pattern",
        "too_short": "Too few items",
        "too_long": "Too many items",
        "greater_than": "Too small",
        "greater_than_equal": "Too small",
        "less_than": "Too large",
        "less_than_equal": "Too large",
        "value_error": FALLBACK_FIELD_MESSAGE,
        "assertion_error": FALLBACK_FIELD_MESSAGE,
    }
)


def _domain_error_status(error: DomainError) -> int:
    for error_class in type(error).__mro__:
        if issubclass(error_class, DomainError) and error_class in DOMAIN_ERROR_STATUS:
            return DOMAIN_ERROR_STATUS[error_class]
    return FALLBACK_DOMAIN_ERROR_STATUS


def _to_field_error(raw: ErrorDetails) -> FieldError:
    error_type = raw["type"]
    return FieldError(
        location=raw["loc"],
        message=FIELD_ERROR_MESSAGES.get(error_type, FALLBACK_FIELD_MESSAGE),
        type=error_type,
    )


async def _handle_domain_error(_request: Request, error: DomainError) -> Response:
    return problem_response(_domain_error_status(error), error.code, error.message)


async def _handle_validation_error(_request: Request, error: RequestValidationError) -> Response:
    return problem_response(
        HTTPStatus.UNPROCESSABLE_CONTENT,
        VALIDATION_FAILED_CODE,
        VALIDATION_FAILED_DETAIL,
        tuple(_to_field_error(raw) for raw in error.errors()),
    )


def _public_detail(detail: object, status_code: int) -> str | None:
    if isinstance(detail, str) and status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
        return detail
    return None


async def _handle_http_exception(_request: Request, error: StarletteHTTPException) -> Response:
    known = known_status(error.status_code)
    code = known.name.lower() if known else UNKNOWN_HTTP_ERROR_CODE
    response = problem_response(
        error.status_code, code, _public_detail(error.detail, error.status_code)
    )
    if error.headers:
        response.headers.update(error.headers)
    return response


def install_error_handlers(app: FastAPI) -> None:
    app.exception_handler(DomainError)(_handle_domain_error)
    app.exception_handler(RequestValidationError)(_handle_validation_error)
    app.exception_handler(StarletteHTTPException)(_handle_http_exception)
