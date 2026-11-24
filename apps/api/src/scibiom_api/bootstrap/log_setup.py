import logging

from scibiom_infrastructure.observability.logging import LogLevel, configure_logging

PROPAGATING_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error")
UVICORN_ACCESS_LOGGER = "uvicorn.access"
HTTP_CLIENT_LOGGERS = ("httpx", "httpx2")


def configure_api_logging(level: LogLevel) -> None:
    configure_logging(level)
    for name in PROPAGATING_UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # Uvicorn's access line contains the full request target, query string included.
    logging.getLogger(UVICORN_ACCESS_LOGGER).disabled = True
    # HTTP clients log every outbound URL, query string included, at INFO.
    for name in HTTP_CLIENT_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
