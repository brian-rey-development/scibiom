import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, override

from scibiom_infrastructure.observability.request_context import current_request_id

if TYPE_CHECKING:
    from types import TracebackType

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

_MAX_EXCEPTION_CAUSES = 5
_CORE_KEYS = frozenset({"timestamp", "level", "logger", "message", "request_id", "exception"})
_RESERVED_KEYS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"} | _CORE_KEYS


class JsonFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {**_core_fields(record), **_extra_fields(record)}
        return json.dumps(payload, default=_type_name_only, separators=(",", ":"))


def _type_name_only(value: object) -> str:
    return f"<{type(value).__qualname__}>"


def _core_fields(record: logging.LogRecord) -> dict[str, object]:
    fields: dict[str, object] = {
        "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }
    request_id = current_request_id()
    if request_id is not None:
        fields["request_id"] = request_id
    if record.exc_info:
        fields["exception"] = _exception_summary(record.exc_info)
    return fields


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    return {key: value for key, value in vars(record).items() if key not in _RESERVED_KEYS}


def _qualified_name(error_type: type[BaseException]) -> str:
    return f"{error_type.__module__}.{error_type.__qualname__}"


def _next_cause(error: BaseException) -> BaseException | None:
    if error.__cause__ is not None or error.__suppress_context__:
        return error.__cause__
    return error.__context__


def _cause_types(error: BaseException) -> list[str]:
    causes: list[str] = []
    cause = _next_cause(error)
    while cause is not None and len(causes) < _MAX_EXCEPTION_CAUSES:
        causes.append(_qualified_name(type(cause)))
        cause = _next_cause(cause)
    return causes


def _exception_summary(
    exc_info: tuple[type[BaseException], BaseException, TracebackType | None]
    | tuple[None, None, None],
) -> dict[str, object]:
    exc_type, error, tb = exc_info
    if exc_type is None or error is None:
        return {}
    return {
        "type": _qualified_name(exc_type),
        "causes": _cause_types(error),
        "stack": "".join(traceback.format_tb(tb)),
    }


def configure_logging(level: LogLevel) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
