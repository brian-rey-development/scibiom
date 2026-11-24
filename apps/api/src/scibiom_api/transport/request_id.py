import re
import uuid
from typing import TYPE_CHECKING

from starlette.datastructures import Headers, MutableHeaders

from scibiom_infrastructure.observability.request_context import bound_request_id

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "x-request-id"
MAX_REQUEST_ID_LENGTH = 128
VALID_REQUEST_ID = re.compile(rf"[A-Za-z0-9._-]{{1,{MAX_REQUEST_ID_LENGTH}}}")


def _resolve_request_id(incoming: str | None) -> str:
    if incoming is not None and VALID_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        request_id = _resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        with bound_request_id(request_id):
            await self._app(scope, receive, send_with_request_id)
