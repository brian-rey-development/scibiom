import json
import logging
from typing import TYPE_CHECKING

import pytest

from scibiom_infrastructure.observability.logging import JsonFormatter, configure_logging
from scibiom_infrastructure.observability.request_context import bound_request_id

if TYPE_CHECKING:
    from collections.abc import Iterator

PRIVATE_DETAIL = "patient-123-secret"
MAX_LOGGED_CAUSES = 5


def _format(record: logging.LogRecord) -> dict[str, object]:
    parsed: dict[str, object] = json.loads(JsonFormatter().format(record))
    return parsed


def _record(message: str = "hello", **extra: object) -> logging.LogRecord:
    return logging.makeLogRecord(
        {"name": "scibiom.test", "levelname": "INFO", "msg": message, "args": (), **extra}
    )


def test_output_is_single_json_line_with_core_fields() -> None:
    line = JsonFormatter().format(_record())
    parsed = json.loads(line)

    assert "\n" not in line
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "scibiom.test"
    assert parsed["message"] == "hello"
    assert parsed["timestamp"].endswith("+00:00")


def test_message_arguments_are_interpolated() -> None:
    record = logging.makeLogRecord({"msg": "count=%d", "args": (3,)})

    assert _format(record)["message"] == "count=3"


def test_request_id_is_included_when_bound() -> None:
    with bound_request_id("req-1"):
        parsed = _format(_record())

    assert parsed["request_id"] == "req-1"


def test_request_id_is_omitted_when_unbound() -> None:
    assert "request_id" not in _format(_record())


def test_extra_fields_are_included_and_standard_attributes_are_not_duplicated() -> None:
    parsed = _format(_record(check="database", error_type="TimeoutError"))

    assert parsed["check"] == "database"
    assert parsed["error_type"] == "TimeoutError"
    assert "args" not in parsed
    assert "msg" not in parsed
    assert "levelname" not in parsed


def _raise_value_error() -> None:
    raise ValueError(PRIVATE_DETAIL)


def test_exception_has_type_and_stack_but_never_the_message() -> None:
    with pytest.raises(ValueError, match=PRIVATE_DETAIL) as excinfo:
        _raise_value_error()
    record = _record(exc_info=(excinfo.type, excinfo.value, excinfo.tb))

    line = JsonFormatter().format(record)
    exception = json.loads(line)["exception"]

    assert exception["type"] == "builtins.ValueError"
    assert "_raise_value_error" in exception["stack"]
    assert PRIVATE_DETAIL not in line


def test_extra_fields_cannot_overwrite_core_keys() -> None:
    parsed = _format(_record(level="FAKE", logger="fake", timestamp="fake", request_id="fake"))

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "scibiom.test"
    assert parsed["timestamp"] != "fake"
    assert "request_id" not in parsed


@pytest.fixture
def restored_root_logger() -> Iterator[None]:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


@pytest.mark.usefixtures("restored_root_logger")
def test_configure_logging_writes_json_lines_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    logging.getLogger("scibiom.test").info("started")

    parsed = json.loads(capsys.readouterr().out)
    assert parsed["message"] == "started"
    assert parsed["logger"] == "scibiom.test"


def _raise_wrapped_error() -> None:
    try:
        int(PRIVATE_DETAIL)
    except ValueError as error:
        message = f"could not parse {PRIVATE_DETAIL}"
        raise RuntimeError(message) from error


def test_exception_lists_cause_types_but_never_their_messages() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        _raise_wrapped_error()
    record = _record(exc_info=(excinfo.type, excinfo.value, excinfo.tb))

    line = JsonFormatter().format(record)
    exception = json.loads(line)["exception"]

    assert exception["type"] == "builtins.RuntimeError"
    assert exception["causes"] == ["builtins.ValueError"]
    assert PRIVATE_DETAIL not in line


def test_non_json_extra_values_are_logged_as_their_type_name_only() -> None:
    line = JsonFormatter().format(_record(error=ValueError(PRIVATE_DETAIL)))

    assert json.loads(line)["error"] == "<ValueError>"
    assert PRIVATE_DETAIL not in line


def _chained_error(depth: int) -> RuntimeError:
    error = RuntimeError()
    for _ in range(depth):
        wrapper = RuntimeError()
        wrapper.__cause__ = error
        error = wrapper
    return error


def test_exception_causes_are_capped() -> None:
    error = _chained_error(MAX_LOGGED_CAUSES + 3)
    record = _record(exc_info=(RuntimeError, error, None))

    exception = json.loads(JsonFormatter().format(record))["exception"]

    assert len(exception["causes"]) == MAX_LOGGED_CAUSES
