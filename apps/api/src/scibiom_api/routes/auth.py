from http import HTTPStatus

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field

from scibiom_api.transport.dependencies import (
    EnvironmentDep,
    RequestSignInCodeDep,
    VerifySignInCodeDep,
)
from scibiom_api.transport.problems import ProblemDetails
from scibiom_api.transport.session_cookie import set_session_cookie
from scibiom_core.identity.domain.email import MAX_EMAIL_LENGTH
from scibiom_core.identity.domain.session import SESSION_LIFETIME

CODE_PATTERN = r"^[0-9]{6}$"

router = APIRouter(prefix="/auth", tags=["auth"])


class SignInCodeRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(max_length=MAX_EMAIL_LENGTH)


class SessionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    code: str = Field(pattern=CODE_PATTERN)


@router.post(
    "/codes",
    operation_id="request_sign_in_code",
    status_code=HTTPStatus.ACCEPTED,
    response_class=Response,
    responses={
        HTTPStatus.UNPROCESSABLE_CONTENT.value: {"model": ProblemDetails},
        HTTPStatus.SERVICE_UNAVAILABLE.value: {"model": ProblemDetails},
    },
)
async def request_sign_in_code(
    body: SignInCodeRequest,
    use_case: RequestSignInCodeDep,
) -> None:
    await use_case(body.email)


@router.post(
    "/sessions",
    operation_id="create_session",
    status_code=HTTPStatus.NO_CONTENT,
    responses={
        HTTPStatus.UNAUTHORIZED.value: {"model": ProblemDetails},
        HTTPStatus.UNPROCESSABLE_CONTENT.value: {"model": ProblemDetails},
    },
)
async def create_session(
    body: SessionRequest,
    use_case: VerifySignInCodeDep,
    environment: EnvironmentDep,
    response: Response,
) -> None:
    token = await use_case(body.email, body.code)
    set_session_cookie(response, token, environment, SESSION_LIFETIME)
