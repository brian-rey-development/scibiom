from http import HTTPStatus
from importlib.metadata import version
from typing import Any

from fastapi import FastAPI

from scibiom_api.bootstrap.container import ContainerFactory, build_container
from scibiom_api.bootstrap.lifespan import build_lifespan
from scibiom_api.bootstrap.log_setup import configure_api_logging
from scibiom_api.bootstrap.settings import ApiSettings, load_settings
from scibiom_api.routes.health import router as health_router
from scibiom_api.transport.error_handlers import install_error_handlers
from scibiom_api.transport.middleware import install_middleware
from scibiom_api.transport.problems import ProblemDetails

API_TITLE = "Scibiom API"
API_VERSION = version("scibiom-api")
DOCS_URL = "/docs"
OPENAPI_URL = "/openapi.json"
APP_RESPONSES: dict[int | str, dict[str, Any]] = {
    HTTPStatus.INTERNAL_SERVER_ERROR.value: {"model": ProblemDetails},
}


def create_app(
    settings: ApiSettings | None = None,
    container_factory: ContainerFactory = build_container,
) -> FastAPI:
    active_settings = settings if settings is not None else load_settings()
    configure_api_logging(active_settings.log_level)
    docs_enabled = active_settings.interactive_docs_enabled
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        lifespan=build_lifespan(active_settings, container_factory),
        docs_url=DOCS_URL if docs_enabled else None,
        openapi_url=OPENAPI_URL if docs_enabled else None,
        redoc_url=None,
        responses=APP_RESPONSES,
    )
    install_middleware(app, active_settings)
    install_error_handlers(app)
    app.include_router(health_router)
    return app
