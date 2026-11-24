from http import HTTPStatus

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from scibiom_infrastructure.observability.request_context import current_request_id

PROBLEM_MEDIA_TYPE = "application/problem+json"
UNKNOWN_STATUS_TITLE = "Error"


class FieldError(BaseModel):
    model_config = ConfigDict(frozen=True)

    location: tuple[str | int, ...]
    message: str
    type: str


class ProblemDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str | None = None
    request_id: str | None = None
    errors: tuple[FieldError, ...] | None = None


def known_status(status: int) -> HTTPStatus | None:
    try:
        return HTTPStatus(status)
    except ValueError:
        return None


def problem_response(
    status: int,
    code: str,
    detail: str | None = None,
    errors: tuple[FieldError, ...] | None = None,
) -> JSONResponse:
    known = known_status(status)
    problem = ProblemDetails(
        title=known.phrase if known else UNKNOWN_STATUS_TITLE,
        status=status,
        code=code,
        detail=detail,
        request_id=current_request_id(),
        errors=errors,
    )
    return JSONResponse(
        problem.model_dump(mode="json", exclude_none=True),
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
    )
