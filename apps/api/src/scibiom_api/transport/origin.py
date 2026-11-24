from http import HTTPStatus
from typing import TYPE_CHECKING

from starlette.datastructures import Headers

from scibiom_api.transport.problems import problem_response

if TYPE_CHECKING:
    from collections.abc import Iterable

    from starlette.types import ASGIApp, Receive, Scope, Send

ORIGIN_HEADER = "origin"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
FORBIDDEN_CODE = "forbidden"
FORBIDDEN_DETAIL = "Request origin is not allowed"


class OriginMiddleware:
    # Browsers always send Origin on unsafe methods, so a missing header means a non-browser
    # client that holds no victim's cookie.
    def __init__(self, app: ASGIApp, allowed_origins: Iterable[str]) -> None:
        self._app = app
        self._allowed_origins = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in UNSAFE_METHODS:
            await self._app(scope, receive, send)
            return
        origins = Headers(scope=scope).getlist(ORIGIN_HEADER)
        if all(origin in self._allowed_origins for origin in origins):
            await self._app(scope, receive, send)
            return
        response = problem_response(HTTPStatus.FORBIDDEN, FORBIDDEN_CODE, FORBIDDEN_DETAIL)
        await response(scope, receive, send)
