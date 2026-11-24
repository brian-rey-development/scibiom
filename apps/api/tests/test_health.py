from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastapi.testclient import TestClient

    from scibiom_core.kernel.readiness import ReadinessCheck


def test_live_reports_ok(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_ready_reports_ready_when_every_check_passes(
    client_for_checks: Callable[[Sequence[ReadinessCheck]], TestClient],
    passing_check: ReadinessCheck,
) -> None:
    response = client_for_checks((passing_check,)).get("/health/ready")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "status": "ready",
        "checks": [{"name": "passing", "status": "pass"}],
    }


def test_ready_reports_not_ready_with_503_when_a_check_fails(
    client_for_checks: Callable[[Sequence[ReadinessCheck]], TestClient],
    passing_check: ReadinessCheck,
    failing_check: ReadinessCheck,
) -> None:
    response = client_for_checks((passing_check, failing_check)).get("/health/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    body = response.json()
    assert body["status"] == "not_ready"
    assert {"name": "failing", "status": "fail"} in body["checks"]
