import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from scibiom_api.transport.problems import problem_response

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

INTERNAL_ERROR_CODE = "internal_error"


class UnhandledErrorMiddleware:
    # Starlette's ServerErrorMiddleware sits outside user middleware, so a 500 built there
    # would miss the request-id scope and header; this one answers from inside it.
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        response_started = False

        async def track_start(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self._app(scope, receive, track_start)
        except Exception:
            if response_started:
                raise
            logger.exception("unhandled_exception")
            response = problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, INTERNAL_ERROR_CODE)
            await response(scope, receive, send)
