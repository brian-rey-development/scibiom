import json
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import pytest
    from fastapi.testclient import TestClient

    from scibiom_core.kernel.readiness import ReadinessCheck

EMAIL = "someone@example.com"
QUERY_STRING = f"email={EMAIL}"
ACCESS_LOG_MESSAGE = "http_request"


def _access_records(output: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = [json.loads(line) for line in output.splitlines()]
    return [record for record in records if record["message"] == ACCESS_LOG_MESSAGE]


def test_logs_the_route_template_and_never_the_query(
    client_for_checks: Callable[[Sequence[ReadinessCheck]], TestClient],
    passing_check: ReadinessCheck,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_for_checks((passing_check,)).get(f"/health/live?{QUERY_STRING}")

    output = capsys.readouterr().out
    (record,) = _access_records(output)
    assert record["route"] == "/health/live"
    assert record["status_code"] == HTTPStatus.OK
    assert EMAIL not in output


def test_logs_unmatched_for_requests_that_match_no_route(
    client_for_checks: Callable[[Sequence[ReadinessCheck]], TestClient],
    passing_check: ReadinessCheck,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_for_checks((passing_check,)).get(f"/patients/someone?{QUERY_STRING}")

    output = capsys.readouterr().out
    (record,) = _access_records(output)
    assert record["route"] == "unmatched"
    assert record["status_code"] == HTTPStatus.NOT_FOUND
    assert "patients" not in output
