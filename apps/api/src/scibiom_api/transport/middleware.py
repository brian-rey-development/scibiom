from typing import TYPE_CHECKING

from starlette.middleware.cors import CORSMiddleware

from scibiom_api.transport.access_log import AccessLogMiddleware
from scibiom_api.transport.request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from scibiom_api.transport.unhandled_errors import UnhandledErrorMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

    from scibiom_api.bootstrap.settings import ApiSettings

CORS_ALLOWED_METHODS = ["GET"]
CORS_ALLOWED_HEADERS = ["Content-Type", REQUEST_ID_HEADER]
CORS_EXPOSED_HEADERS = [REQUEST_ID_HEADER]


def install_middleware(app: FastAPI, settings: ApiSettings) -> None:
    # Request flow is RequestId, AccessLog, CORS, UnhandledError; Starlette makes the last
    # middleware added the outermost, so they are added in reverse.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors.allowed_origins),
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=CORS_EXPOSED_HEADERS,
        allow_credentials=False,
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
