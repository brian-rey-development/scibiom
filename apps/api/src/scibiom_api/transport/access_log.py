import logging
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

UNMATCHED_ROUTE = "unmatched"
MILLISECONDS_PER_SECOND = 1000
DURATION_DECIMALS = 2


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    if isinstance(route, Route):
        return route.path
    return UNMATCHED_ROUTE


def _log_request(scope: Scope, status_code: int, started_at: float) -> None:
    elapsed = time.perf_counter() - started_at
    logger.info(
        "http_request",
        extra={
            "method": scope["method"],
            "route": _route_template(scope),
            "status_code": status_code,
            "duration_ms": round(elapsed * MILLISECONDS_PER_SECOND, DURATION_DECIMALS),
        },
    )


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
        started_at = time.perf_counter()

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, capture_status)
        finally:
            _log_request(scope, status_code, started_at)
