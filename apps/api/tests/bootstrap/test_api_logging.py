import json
import logging
from typing import TYPE_CHECKING

from scibiom_api.bootstrap.log_setup import configure_api_logging

if TYPE_CHECKING:
    import pytest

QUERY_STRING = "email=someone@example.com"


def test_uvicorn_access_logger_emits_nothing_after_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_api_logging("INFO")

    logging.getLogger("uvicorn.access").info('GET /health/live?%s "HTTP/1.1" 200', QUERY_STRING)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_uvicorn_error_logger_reaches_the_json_root_handler_exactly_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logging.getLogger("uvicorn.error").addHandler(logging.StreamHandler())

    configure_api_logging("INFO")
    logging.getLogger("uvicorn.error").info("started")

    captured = capsys.readouterr()
    (line,) = captured.out.splitlines()
    record = json.loads(line)
    assert record["logger"] == "uvicorn.error"
    assert record["message"] == "started"
    assert captured.err == ""
