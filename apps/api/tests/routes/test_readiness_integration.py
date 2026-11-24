from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from scibiom_api.bootstrap.settings import load_settings
from scibiom_api.main import create_app

pytestmark = pytest.mark.integration


def test_readiness_passes_against_the_local_database() -> None:
    with TestClient(create_app(load_settings())) as client:
        response = client.get("/health/ready")

    assert response.status_code == HTTPStatus.OK
    checks = {check["name"]: check["status"] for check in response.json()["checks"]}
    assert checks["database"] == "pass"
