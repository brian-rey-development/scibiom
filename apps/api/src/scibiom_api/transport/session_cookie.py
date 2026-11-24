from typing import TYPE_CHECKING

from scibiom_api.bootstrap.settings import HARDENED_ENVIRONMENTS

if TYPE_CHECKING:
    from datetime import timedelta

    from fastapi import Request, Response

    from scibiom_api.bootstrap.settings import Environment

LOCAL_COOKIE_NAME = "scibiom_session"
HARDENED_COOKIE_NAME = "__Host-scibiom_session"
COOKIE_PATH = "/"


def _is_hardened(environment: Environment) -> bool:
    return environment in HARDENED_ENVIRONMENTS


def _cookie_name(environment: Environment) -> str:
    return HARDENED_COOKIE_NAME if _is_hardened(environment) else LOCAL_COOKIE_NAME


def set_session_cookie(
    response: Response, token: str, environment: Environment, max_age: timedelta
) -> None:
    response.set_cookie(
        key=_cookie_name(environment),
        value=token,
        max_age=int(max_age.total_seconds()),
        path=COOKIE_PATH,
        secure=_is_hardened(environment),
        httponly=True,
        samesite="strict",
    )


def read_session_cookie(request: Request, environment: Environment) -> str | None:
    return request.cookies.get(_cookie_name(environment))
